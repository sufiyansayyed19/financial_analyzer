"""
🧠 FinRAG — Semantic Answer Cache
====================================

WHAT THIS DOES:
---------------
Caches RAG answers so identical (or near-identical) questions
get instant responses without calling the Gemini API again.

WHY THIS MATTERS:
──────────────────
1. COST:  Every Gemini API call costs money. If 10 users ask
          "What was NVIDIA's revenue?", we only pay ONCE.
2. SPEED: LLM generation takes 3-8 seconds. Cache hits return
          in <10 milliseconds — a 500x speedup.
3. RATE LIMITS: Gemini has per-minute request limits. Caching
                reduces our API usage dramatically.

HOW IT WORKS:
──────────────
We use a simple in-memory dictionary with a hash of the query +
filters as the key. When a question comes in:
  1. Hash the question + company + year filters
  2. Check if that hash exists in cache
  3. If YES → return cached answer instantly (cache HIT)
  4. If NO  → call the LLM, store the result, return it (cache MISS)

CACHE INVALIDATION:
────────────────────
The cache auto-clears when:
  - A new document is uploaded (new data = old answers may be stale)
  - A document is deleted
  - The server restarts (it's in-memory, not persistent)
  - A cache entry is older than TTL (time-to-live) seconds

WHAT YOU'LL LEARN:
- Caching patterns (in-memory dictionary cache)
- Cache key design (hashing query + filters)
- TTL (time-to-live) expiration
- Cache invalidation strategies
"""

import hashlib
import time
from dataclasses import dataclass, field

from backend.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """A single cached answer."""
    answer: str
    sources: list[dict]
    created_at: float  # Unix timestamp
    retrieval_time: float
    generation_time: float
    total_time: float
    chunks_searched: int


class RAGCache:
    """
    In-memory cache for RAG answers.

    Uses a Python dict for O(1) lookups.
    Thread-safe enough for our use case (single-process uvicorn).

    In production, you'd swap this for Redis:
      - Persists across server restarts
      - Shared across multiple server instances
      - Built-in TTL expiration
    """

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 500):
        """
        Args:
            ttl_seconds: How long cached answers stay valid (default: 1 hour)
            max_size: Maximum number of cached entries (prevents memory bloat)
        """
        self._cache: dict[str, CacheEntry] = {}
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def _make_key(
        self,
        query: str,
        company: str | None = None,
        year: str | None = None,
        region: str | None = None,
    ) -> str:
        """
        Create a unique cache key from query + filters.

        WHY HASH?
        We normalize the query to lowercase and strip whitespace,
        so "What was revenue?" and "what was revenue?" hit the same cache.
        """
        normalized = query.strip().lower()
        key_parts = f"{normalized}|{company or ''}|{year or ''}|{region or ''}"
        return hashlib.sha256(key_parts.encode()).hexdigest()

    def get(
        self,
        query: str,
        company: str | None = None,
        year: str | None = None,
        region: str | None = None,
    ) -> CacheEntry | None:
        """
        Look up a cached answer.

        Returns None on cache miss or if the entry has expired.
        """
        key = self._make_key(query, company, year, region)
        entry = self._cache.get(key)

        if entry is None:
            self.misses += 1
            return None

        # Check TTL expiration
        age = time.time() - entry.created_at
        if age > self.ttl_seconds:
            # Entry is stale — remove it
            del self._cache[key]
            self.misses += 1
            logger.info(f"⏰ Cache expired for: '{query[:40]}...' (age: {age:.0f}s)")
            return None

        self.hits += 1
        logger.info(
            f"⚡ Cache HIT for: '{query[:40]}...' "
            f"(age: {age:.0f}s, saved ~{entry.generation_time:.1f}s)"
        )
        return entry

    def put(
        self,
        query: str,
        answer: str,
        sources: list[dict],
        retrieval_time: float,
        generation_time: float,
        total_time: float,
        chunks_searched: int,
        company: str | None = None,
        year: str | None = None,
        region: str | None = None,
    ) -> None:
        """Store an answer in the cache."""
        # Evict oldest entries if cache is full
        if len(self._cache) >= self.max_size:
            self._evict_oldest()

        key = self._make_key(query, company, year, region)
        self._cache[key] = CacheEntry(
            answer=answer,
            sources=sources,
            created_at=time.time(),
            retrieval_time=retrieval_time,
            generation_time=generation_time,
            total_time=total_time,
            chunks_searched=chunks_searched,
        )
        logger.info(f"💾 Cached answer for: '{query[:40]}...' (cache size: {len(self._cache)})")

    def invalidate(self) -> int:
        """
        Clear the entire cache.

        Called when documents are uploaded or deleted,
        because the answers may now be stale.

        Returns the number of entries cleared.
        """
        count = len(self._cache)
        self._cache.clear()
        if count > 0:
            logger.info(f"🗑️ Cache invalidated: cleared {count} entries")
        return count

    def _evict_oldest(self) -> None:
        """Remove the oldest cache entry to make room."""
        if not self._cache:
            return
        oldest_key = min(self._cache, key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "ttl_seconds": self.ttl_seconds,
        }


# ──────────────────────────────────────────────
# 🎯 SINGLETON — one cache instance for the whole app
# ──────────────────────────────────────────────
rag_cache = RAGCache(ttl_seconds=3600, max_size=500)

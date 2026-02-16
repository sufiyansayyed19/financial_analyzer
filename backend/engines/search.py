"""
🧠 FinRAG — Semantic Search Engine
=====================================

WHAT THIS DOES:
---------------
Finds the most relevant text chunks for a given question/query
by comparing MEANING, not just keywords.

HOW SEMANTIC SEARCH WORKS:
───────────────────────────
Traditional search: "What was revenue?" → only matches chunks containing "revenue"
Semantic search:    "What was revenue?" → also matches "sales figures", "income generated"

Steps:
  1. User asks a question
  2. Embed the question → 384-dimensional vector
  3. Compare against ALL stored chunk vectors
  4. Return the top-K most similar chunks

SEARCH FLOW:
─────────────
    "What was NVIDIA's revenue in 2024?"
              │
              ▼
    embed_text() → [0.12, -0.34, 0.56, ...]  (384 dims)
              │
              ▼
    Load all chunk embeddings from DB
              │
              ▼
    cosine_similarity(query_vec, all_chunk_vecs)
              │
              ▼
    Sort by score → Top 5 results
              │
              ▼
    Return chunks with text + metadata + scores

WHY NUMPY INSTEAD OF pgvector?
────────────────────────────────
With ~25K chunks, numpy cosine similarity on CPU takes <100ms.
pgvector is for millions of vectors. We'll add it in Phase 5
when we migrate to PostgreSQL.

WHAT YOU'LL LEARN:
- How semantic search works end-to-end
- Loading binary embeddings from database
- Filtering search results by metadata
- Result ranking and scoring
"""

from dataclasses import dataclass

import numpy as np

from backend.core.logging import get_logger
from backend.db.database import get_session
from backend.db.models import Chunk
from backend.engines.embedder import cosine_similarity, embed_text

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """
    One search result returned to the user.

    WHY A DATACLASS?
    Instead of returning raw dicts or tuples, we return typed objects.
    This means IDE autocomplete works: result.text, result.score, etc.
    """

    text: str
    score: float
    company: str
    year: str
    region: str
    chunk_index: int
    document_id: int


def search(
    query: str,
    top_k: int = 5,
    company: str | None = None,
    year: str | None = None,
    region: str | None = None,
    score_threshold: float = 0.0,
) -> list[SearchResult]:
    """
    Semantic search over all stored chunks.

    Args:
        query: Natural language question (e.g., "What was NVIDIA's revenue?")
        top_k: Number of results to return (default 5)
        company: Optional filter (e.g., "nvidia")
        year: Optional filter (e.g., "2024")
        region: Optional filter (e.g., "us" or "india")
        score_threshold: Minimum similarity score (0.0–1.0)

    Returns:
        List of SearchResult objects, sorted by relevance (highest first)

    Example:
        >>> results = search("What was NVIDIA's revenue in 2024?", top_k=3)
        >>> for r in results:
        ...     print(f"{r.score:.3f} [{r.company}/{r.year}] {r.text[:80]}...")
    """
    # ── Step 1: Embed the query ──
    query_vec = embed_text(query)

    # ── Step 2: Load chunks from database ──
    session = get_session()

    try:
        # Build query with optional filters
        db_query = session.query(Chunk).filter(Chunk.embedding.isnot(None))

        if company:
            db_query = db_query.filter(Chunk.company == company.lower())
        if year:
            db_query = db_query.filter(Chunk.year == year)
        if region:
            db_query = db_query.filter(Chunk.region == region.lower())

        chunks = db_query.all()

        if not chunks:
            logger.warning("No chunks found matching filters")
            return []

        # ── Step 3: Deserialize embeddings ──
        # Binary blobs → numpy arrays
        embeddings = np.array([
            np.frombuffer(chunk.embedding, dtype=np.float32)
            for chunk in chunks
        ])

        # ── Step 4: Compute similarities ──
        scores = cosine_similarity(query_vec, embeddings)

        # ── Step 5: Rank and filter ──
        # Get indices sorted by score (highest first)
        ranked_indices = np.argsort(scores)[::-1]

        results = []
        for idx in ranked_indices[:top_k]:
            score = float(scores[idx])
            if score < score_threshold:
                break

            chunk = chunks[idx]
            results.append(SearchResult(
                text=chunk.text,
                score=score,
                company=chunk.company,
                year=chunk.year,
                region=chunk.region,
                chunk_index=chunk.chunk_index,
                document_id=chunk.document_id,
            ))

        logger.info(
            f"🔍 Search: '{query[:50]}...' → {len(results)} results "
            f"(from {len(chunks):,} chunks, top score: {results[0].score:.3f})"
            if results else
            f"🔍 Search: '{query[:50]}...' → 0 results"
        )

        return results

    finally:
        session.close()


def search_pretty(
    query: str,
    top_k: int = 5,
    **kwargs,
) -> None:
    """
    Search and print results in a readable format.

    Useful for interactive testing and demos.
    """
    print(f"\n{'='*60}")
    print(f"🔍 Query: {query}")
    print(f"{'='*60}")

    results = search(query, top_k=top_k, **kwargs)

    if not results:
        print("   No results found.")
        return

    for i, r in enumerate(results, 1):
        # Visual score bar
        bar = "█" * int(r.score * 30)
        print(f"\n── Result {i} ─────────────────────────────")
        print(f"   Score:   {r.score:.4f} {bar}")
        print(f"   Source:  {r.company}/{r.year} ({r.region}) chunk #{r.chunk_index}")
        print(f"   Text:    {r.text[:200]}...")

    print(f"\n{'─'*60}")


# ──────────────────────────────────────────────
# 🧪 TEST: Run directly for interactive search
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 SEMANTIC SEARCH ENGINE TEST")
    print("=" * 60)

    # Test 1: General financial query
    search_pretty("What was the company's total revenue?")

    # Test 2: Company-specific query
    search_pretty(
        "How did NVIDIA's data center business perform?",
        company="nvidia",
    )

    # Test 3: Cross-company comparison
    search_pretty("What are the key risk factors?", top_k=3)

    # Test 4: Year-specific
    search_pretty(
        "What was the dividend paid to shareholders?",
        year="2024",
        top_k=3,
    )

    print("\n💡 Try your own queries!")
    print("   python -c \"from backend.engines.search import search_pretty; search_pretty('your query here')\"")

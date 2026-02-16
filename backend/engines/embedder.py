"""
🧠 FinRAG — Embedding Engine
==============================

WHAT THIS DOES:
---------------
Converts text into NUMBERS (vectors/embeddings) that capture meaning.

WHY EMBEDDINGS MATTER:
-----------------------
Computers can't understand text directly. But they CAN compare numbers.
Embeddings are vectors (lists of numbers) where:
  - Similar meanings → vectors point in similar directions
  - "revenue growth" and "sales increase" → close together
  - "revenue growth" and "employee benefits" → far apart

This is the CORE of semantic search. Without embeddings,
we'd be stuck with keyword matching ("revenue" only matches "revenue",
not "sales" or "income").

HOW IT WORKS:
-------------
1. Load a pre-trained transformer model (all-MiniLM-L6-v2)
2. Pass text through the model → get a 384-dimensional vector
3. Store vectors in database
4. To search: embed the query → find closest stored vectors

MODEL CHOICE — all-MiniLM-L6-v2:
  - 384 dimensions (small = fast)
  - 80MB size (fits anywhere)
  - Trained on 1B+ sentence pairs
  - Top-tier quality for its size on MTEB benchmark
  - Used in production by many RAG systems

WHAT YOU'LL LEARN:
- How sentence-transformers work
- Singleton pattern for expensive model loading
- Batch processing for performance
- Why embedding dimension matters
"""

import time

import numpy as np
from sentence_transformers import SentenceTransformer

from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# 🏗 MODEL LOADING — SINGLETON PATTERN
# ──────────────────────────────────────────────
# Loading a transformer model takes 2-5 seconds and uses ~200MB RAM.
# We do this ONCE and reuse the same model instance everywhere.
#
# WHY SINGLETON?
# If every function call loaded the model fresh, we'd waste seconds
# on every search query. Instead, we load once at module import time.
#
# This is the same pattern we used for `settings` in config.py.

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """
    Get the embedding model (lazy singleton).

    LAZY LOADING: The model isn't loaded until first use.
    This prevents slow imports when you don't need embeddings
    (e.g., when just running the text pipeline).
    """
    global _model
    if _model is None:
        logger.info(f"🔄 Loading embedding model: {settings.embedding_model}...")
        start = time.time()
        _model = SentenceTransformer(settings.embedding_model)
        elapsed = time.time() - start
        logger.info(f"✅ Model loaded in {elapsed:.1f}s ({settings.embedding_dim}D vectors)")
    return _model


# ──────────────────────────────────────────────
# 🎯 CORE FUNCTIONS
# ──────────────────────────────────────────────


def embed_text(text: str) -> np.ndarray:
    """
    Embed a single text string → 384-dimensional vector.

    Args:
        text: Any text string (query, chunk, sentence)

    Returns:
        numpy array of shape (384,) — the embedding vector

    Example:
        >>> vec = embed_text("NVIDIA reported record revenue")
        >>> vec.shape
        (384,)
    """
    model = get_model()
    # encode() returns a numpy array
    # normalize_embeddings=True → unit vectors → cosine similarity = dot product
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding


def embed_batch(
    texts: list[str],
    batch_size: int = 64,
    show_progress: bool = True,
) -> np.ndarray:
    """
    Embed multiple texts efficiently using batching.

    WHY BATCHING?
    Processing texts one-by-one is slow because:
    1. Each call has overhead (data transfer to model)
    2. GPUs/CPUs are optimized for parallel operations

    Batching groups texts together → much faster.
    64 texts at once ≈ 50x faster than one at a time.

    Args:
        texts: List of text strings to embed
        batch_size: How many texts to process together (default 64)
        show_progress: Whether to log progress

    Returns:
        numpy array of shape (n_texts, 384) — one vector per text
    """
    model = get_model()

    if show_progress:
        logger.info(f"📊 Embedding {len(texts):,} texts (batch_size={batch_size})...")

    start = time.time()

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=show_progress,
    )

    elapsed = time.time() - start

    if show_progress:
        rate = len(texts) / elapsed if elapsed > 0 else 0
        logger.info(
            f"✅ Embedded {len(texts):,} texts in {elapsed:.1f}s "
            f"({rate:.0f} texts/sec)"
        )

    return embeddings


def cosine_similarity(query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between a query and multiple document vectors.

    COSINE SIMILARITY EXPLAINED:
    ─────────────────────────────
    Measures the ANGLE between two vectors (not distance).

    cos(θ) = (A · B) / (||A|| × ||B||)

    - 1.0 = identical direction (same meaning)
    - 0.0 = perpendicular (unrelated)
    - -1.0 = opposite direction (opposite meaning)

    WHY COSINE OVER EUCLIDEAN?
    Cosine doesn't care about vector LENGTH, only direction.
    A short document and a long document about the same topic
    will have similar cosine scores but very different Euclidean distances.

    OPTIMIZATION: Since we normalize embeddings to unit vectors
    during encoding, cosine similarity = simple dot product.
    This is why we set normalize_embeddings=True in embed_text().

    Args:
        query_vec: Shape (384,) — the query embedding
        doc_vecs: Shape (n, 384) — document embeddings

    Returns:
        Shape (n,) — similarity scores for each document
    """
    # Dot product of normalized vectors = cosine similarity
    # This is a matrix multiplication: (1, 384) × (384, n) = (1, n)
    scores = np.dot(doc_vecs, query_vec)
    return scores


# ──────────────────────────────────────────────
# 🧪 TEST: Run directly to see embeddings in action
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 EMBEDDING ENGINE TEST")
    print("=" * 60)

    # Test 1: Single embedding
    print("\n--- Test 1: Single Embedding ---")
    vec = embed_text("NVIDIA reported record revenue of $60.9 billion")
    print(f"Shape: {vec.shape}")
    print(f"First 5 values: {vec[:5]}")
    print(f"Norm (should be ~1.0): {np.linalg.norm(vec):.4f}")

    # Test 2: Batch embedding
    print("\n--- Test 2: Batch Embedding ---")
    texts = [
        "NVIDIA reported record revenue",
        "Sales growth was exceptional this quarter",
        "Employee benefits program expanded",
        "The weather in Tokyo is sunny",
    ]
    vecs = embed_batch(texts, show_progress=False)
    print(f"Shape: {vecs.shape}")

    # Test 3: Semantic similarity
    print("\n--- Test 3: Semantic Similarity ---")
    query = embed_text("How much money did the company make?")

    for i, text in enumerate(texts):
        score = cosine_similarity(query, vecs[i : i + 1])[0]
        bar = "█" * int(score * 40)
        print(f"  {score:.3f} {bar} {text}")

    print("\n💡 Notice: 'revenue' and 'sales growth' score high,")
    print("   'employee benefits' and 'weather' score low.")
    print("   THIS is semantic search in action!")

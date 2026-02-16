"""
🧠 FinRAG — Embedding Storage Pipeline
=========================================

WHAT THIS DOES:
---------------
Reads processed chunk files → generates embeddings → stores in database.

This is the BRIDGE between Phase 1 (text processing) and Phase 2 (search).

PIPELINE FLOW:
──────────────
  _chunks.json files (from Phase 1)
        │
        ▼
  Load chunks + metadata
        │
        ▼
  Generate embeddings (batch processing)
        │
        ▼
  Store in SQLite (text + embedding + metadata)
        │
        ▼
  Ready for semantic search!

WHAT YOU'LL LEARN:
- How to connect pipeline stages across phases
- Batch processing for performance
- Binary serialization of numpy arrays
- Idempotent data loading (skip if already exists)
"""

import json
import time
from pathlib import Path

import numpy as np

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.db.database import get_session, init_db
from backend.db.models import Chunk, Document
from backend.engines.embedder import embed_batch

logger = get_logger(__name__)


def load_chunks_from_file(chunks_path: Path) -> list[dict]:
    """
    Load chunks from a _chunks.json file.

    Each chunk file contains an array of objects with:
      - text: the chunk content
      - chunk_index: position in document
      - metadata: company, year, region, etc.
    """
    with open(chunks_path, encoding="utf-8") as f:
        data = json.load(f)

    # Handle both formats: list of chunks or dict with "chunks" key
    if isinstance(data, dict):
        return data.get("chunks", [])
    return data


def store_document_embeddings(
    chunks_path: Path,
    session,
    batch_size: int = 64,
) -> int:
    """
    Process one document: load chunks → embed → store.

    Returns the number of chunks stored.
    """
    # ── Parse metadata from file path ──
    # Path pattern: processed/{region}/annual/{company}/{company}_{year}_annual_chunks.json
    file_name = chunks_path.stem.replace("_chunks", "")  # e.g., "nvidia_2024_annual"
    parts = chunks_path.parts

    # Find region and company from path
    try:
        # Walk up the path to find the structure
        processed_idx = None
        for i, part in enumerate(parts):
            if part == "processed":
                processed_idx = i
                break

        if processed_idx is not None:
            region = parts[processed_idx + 1]     # "us" or "india"
            company = parts[processed_idx + 3]    # "nvidia", "hdfc", etc.
        else:
            region = "unknown"
            company = "unknown"
    except (IndexError, ValueError):
        region = "unknown"
        company = "unknown"

    # Extract year from filename (e.g., "nvidia_2024_annual" → "2024")
    year = "unknown"
    for part in file_name.split("_"):
        if part.isdigit() and len(part) == 4:
            year = part
            break

    # ── Check if already stored (idempotency) ──
    existing = session.query(Document).filter_by(
        file_name=f"{file_name}.pdf"
    ).first()

    if existing:
        logger.info(f"   ⏭️  Already stored: {file_name} ({existing.total_chunks} chunks)")
        return 0

    # ── Load chunks ──
    raw_chunks = load_chunks_from_file(chunks_path)
    if not raw_chunks:
        logger.warning(f"   ⚠️  No chunks in {chunks_path.name}")
        return 0

    # Extract texts for embedding
    texts = [c.get("text", "") for c in raw_chunks]

    # ── Generate embeddings ──
    logger.info(f"   🔄 Embedding {len(texts)} chunks for {file_name}...")
    embeddings = embed_batch(texts, batch_size=batch_size, show_progress=False)

    # ── Create Document record ──
    doc = Document(
        file_name=f"{file_name}.pdf",
        company=company,
        year=year,
        region=region,
        report_type="annual",
        total_chunks=len(raw_chunks),
    )
    session.add(doc)
    session.flush()  # Get the auto-generated doc.id

    # ── Create Chunk records ──
    chunk_objects = []
    for i, (raw_chunk, embedding) in enumerate(zip(raw_chunks, embeddings)):
        chunk = Chunk(
            document_id=doc.id,
            chunk_index=raw_chunk.get("chunk_index", i),
            text=raw_chunk.get("text", ""),
            embedding=embedding.astype(np.float32).tobytes(),
            company=company,
            year=year,
            region=region,
            char_count=len(raw_chunk.get("text", "")),
        )
        chunk_objects.append(chunk)

    session.bulk_save_objects(chunk_objects)
    session.commit()

    logger.info(f"   ✅ Stored {len(chunk_objects)} chunks for {file_name}")
    return len(chunk_objects)


def run_embedding_pipeline() -> dict:
    """
    Embed and store ALL processed documents.

    Returns a summary dict with stats.
    """
    logger.info("=" * 60)
    logger.info("🚀 EMBEDDING STORAGE PIPELINE")
    logger.info("=" * 60)

    start = time.time()

    # Initialize database
    init_db()

    # Find all chunk files
    chunk_files = sorted(settings.processed_dir.rglob("*_chunks.json"))
    logger.info(f"📂 Found {len(chunk_files)} chunk files to process")

    if not chunk_files:
        logger.warning("No chunk files found! Run the ingestion pipeline first.")
        return {"total_files": 0, "total_chunks": 0}

    session = get_session()
    total_stored = 0
    files_processed = 0
    files_skipped = 0

    try:
        for i, chunk_file in enumerate(chunk_files, 1):
            logger.info(f"\n[{i}/{len(chunk_files)}] {chunk_file.stem}")

            stored = store_document_embeddings(chunk_file, session)

            if stored > 0:
                total_stored += stored
                files_processed += 1
            else:
                files_skipped += 1

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()

    elapsed = time.time() - start

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 EMBEDDING PIPELINE SUMMARY")
    logger.info("=" * 60)
    logger.info(f"   Files processed: {files_processed}")
    logger.info(f"   Files skipped:   {files_skipped}")
    logger.info(f"   Total chunks:    {total_stored:,}")
    logger.info(f"   Time:            {elapsed:.1f}s")
    if total_stored > 0:
        logger.info(f"   Rate:            {total_stored/elapsed:.0f} chunks/sec")
    logger.info("=" * 60)

    return {
        "files_processed": files_processed,
        "files_skipped": files_skipped,
        "total_chunks": total_stored,
        "elapsed_seconds": round(elapsed, 1),
    }


# ──────────────────────────────────────────────
# 🧪 CLI ENTRY POINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    summary = run_embedding_pipeline()
    print(f"\n✅ Done! {summary['total_chunks']:,} chunks embedded and stored.")

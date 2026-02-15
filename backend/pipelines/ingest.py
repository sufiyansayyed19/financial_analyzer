"""
🧠 FinRAG — End-to-End Ingestion Pipeline
============================================

WHAT THIS DOES:
---------------
Orchestrates the FULL pipeline:

    PDF → Extract Text → Clean → Chunk → Save to Disk

This processes ALL 21 PDFs and saves structured output.

WHY THIS IS A SEPARATE FILE:
------------------------------
We built each step as an independent, reusable component:
- pdf_extractor.py → can be used alone for extraction
- text_cleaner.py  → can be used alone for cleaning
- chunker.py       → can be used alone for chunking

This file ORCHESTRATES them. This is the "Service Layer" pattern:
components don't know about each other, the orchestrator connects them.

WHAT GETS SAVED:
-----------------
For each PDF, we save:

processed/
├── us/annual/nvidia/
│   ├── nvidia_2024_annual.txt        ← full cleaned text
│   └── nvidia_2024_annual_chunks.json ← all chunks with metadata

WHY BOTH FORMATS?
- .txt  → human-readable, easy to inspect
- .json → machine-readable, structured data for Phase 2 (database loading)

WHAT YOU'LL LEARN:
- Pipeline orchestration pattern
- JSON serialization of dataclasses
- Error handling in batch processing
- Idempotent design (safe to re-run)
"""

import json
import time
from dataclasses import asdict
from pathlib import Path

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.pipelines.chunker import ChunkedDocument, chunk_text
from backend.pipelines.pdf_extractor import ExtractedDocument, extract_all_pdfs
from backend.pipelines.text_cleaner import CleaningStats, clean_document_text

logger = get_logger(__name__)


def save_processed_output(
    doc: ExtractedDocument,
    cleaned_text: str,
    cleaning_stats: CleaningStats,
    chunked_doc: ChunkedDocument,
) -> Path:
    """
    Save processed output to disk.

    Creates directory structure mirroring the input:
        data/us/annual/nvidia/nvidia_2024.pdf
        → processed/us/annual/nvidia/nvidia_2024_annual.txt
        → processed/us/annual/nvidia/nvidia_2024_annual_chunks.json

    WHY MIRROR THE STRUCTURE?
    → Makes it obvious which output corresponds to which input.
    → Later, when we load into the database, we can walk the tree.

    IDEMPOTENT DESIGN:
    → Running this twice produces the same result.
    → Existing files get overwritten (no duplicates).
    """
    # Build output directory: processed/region/report_type/company/
    output_dir = (
        settings.processed_dir
        / doc.region
        / doc.report_type
        / doc.company
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Save cleaned text (.txt) ──
    txt_filename = doc.file_path.stem + ".txt"
    txt_path = output_dir / txt_filename
    txt_path.write_text(cleaned_text, encoding="utf-8")

    # ── Save chunks (.json) ──
    json_filename = doc.file_path.stem + "_chunks.json"
    json_path = output_dir / json_filename

    # Convert dataclass → dict for JSON serialization
    chunks_data = {
        "metadata": {
            "company": doc.company,
            "year": doc.year,
            "region": doc.region,
            "report_type": doc.report_type,
            "source_file": doc.file_name,
            "total_pages": doc.total_pages,
            "original_chars": cleaning_stats.original_chars,
            "cleaned_chars": cleaning_stats.cleaned_chars,
            "reduction_percent": round(cleaning_stats.reduction_percent, 2),
            "total_chunks": len(chunked_doc.chunks),
            "avg_chunk_size": round(chunked_doc.avg_chunk_size, 0),
        },
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "char_count": chunk.char_count,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
            }
            for chunk in chunked_doc.chunks
        ],
    }

    json_path.write_text(
        json.dumps(chunks_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info(f"   💾 Saved: {txt_path.name} + {json_path.name}")

    return output_dir


def run_ingestion_pipeline(data_dir: Path | None = None) -> dict:
    """
    Run the complete ingestion pipeline on all PDFs.

    This is the MAIN ENTRY POINT for Phase 1.

    Returns:
        Summary dict with counts and statistics.
    """
    data_dir = data_dir or settings.data_dir
    start_time = time.time()

    logger.info("=" * 60)
    logger.info("🚀 FINRAG INGESTION PIPELINE — STARTING")
    logger.info("=" * 60)

    # ── Step 1: Extract all PDFs ──
    logger.info("\n📑 STEP 1: Extracting text from PDFs...")
    documents = extract_all_pdfs(data_dir)

    if not documents:
        logger.error("No documents extracted. Aborting.")
        return {"success": False, "error": "No documents found"}

    # ── Step 2 & 3: Clean and Chunk each document ──
    logger.info("\n🧹 STEP 2 & 3: Cleaning and chunking...")

    total_chunks = 0
    successful = 0
    failed = 0
    results_summary = []

    for doc in documents:
        if not doc.extraction_success:
            failed += 1
            logger.warning(f"   ⏭️  Skipping {doc.file_name} (extraction failed)")
            continue

        try:
            # Clean
            cleaned_text, cleaning_stats = clean_document_text(
                doc.full_text,
                company=doc.company,
                year=doc.year,
            )

            # Chunk
            chunked_doc = chunk_text(
                cleaned_text,
                company=doc.company,
                year=doc.year,
                region=doc.region,
                report_type=doc.report_type,
            )

            # Save
            save_processed_output(doc, cleaned_text, cleaning_stats, chunked_doc)

            total_chunks += len(chunked_doc.chunks)
            successful += 1

            results_summary.append({
                "file": doc.file_name,
                "company": doc.company,
                "year": doc.year,
                "pages": doc.total_pages,
                "chunks": len(chunked_doc.chunks),
                "chars_original": cleaning_stats.original_chars,
                "chars_cleaned": cleaning_stats.cleaned_chars,
            })

        except Exception as e:
            failed += 1
            logger.error(f"   ❌ Failed processing {doc.file_name}: {e}")

    # ── Summary ──
    elapsed = time.time() - start_time

    logger.info("\n" + "=" * 60)
    logger.info("📊 INGESTION PIPELINE — COMPLETE")
    logger.info("=" * 60)
    logger.info(f"   ✅ Successful:   {successful}/{len(documents)}")
    logger.info(f"   ❌ Failed:       {failed}/{len(documents)}")
    logger.info(f"   📦 Total chunks: {total_chunks:,}")
    logger.info(f"   ⏱️  Time:        {elapsed:.1f} seconds")
    logger.info(f"   💾 Output:       {settings.processed_dir}")

    # Save pipeline summary
    summary = {
        "pipeline_run": {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_documents": len(documents),
            "successful": successful,
            "failed": failed,
            "total_chunks": total_chunks,
            "elapsed_seconds": round(elapsed, 1),
        },
        "documents": results_summary,
    }

    summary_path = settings.processed_dir / "ingestion_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(f"   📋 Summary saved: {summary_path}")

    return summary


# ──────────────────────────────────────────────
# 🚀 RUN THE PIPELINE
# ──────────────────────────────────────────────
if __name__ == "__main__":
    summary = run_ingestion_pipeline()

    # Print per-document results table
    if "documents" in summary:
        print(f"\n{'─' * 70}")
        print(f"{'File':<35} {'Pages':>6} {'Chunks':>7} {'Chars':>10}")
        print(f"{'─' * 70}")
        for doc in summary["documents"]:
            print(
                f"{doc['file']:<35} "
                f"{doc['pages']:>6} "
                f"{doc['chunks']:>7} "
                f"{doc['chars_cleaned']:>10,}"
            )
        print(f"{'─' * 70}")

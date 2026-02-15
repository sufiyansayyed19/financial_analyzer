"""
🧠 FinRAG — Chunking Engine
==============================

WHAT THIS DOES:
---------------
Splits cleaned document text into small, overlapping "chunks" — the
fundamental knowledge units of our system.

WHY CHUNKING MATTERS (this is CRITICAL for RAG):
-------------------------------------------------
LLMs have a limited context window (4K–128K tokens).
A 300-page annual report has ~500K+ tokens — it won't fit in one prompt.

So we split the text into smaller pieces ("chunks") and later use
vector search to find only the RELEVANT chunks for a query.

THE CHUNKING DILEMMA:
---------------------
Too small (100 chars) → loses context ("revenue increased" — which revenue? what company?)
Too large (5000 chars) → includes too much irrelevant information
Just right (500-1500 chars) → captures a complete idea with context

WHY OVERLAP?
------------
If we chunk without overlap, we might split a sentence in half:

    Chunk 1: "...NVIDIA reported total revenue of"
    Chunk 2: "$60.9 billion, a 126% increase..."

With 200-char overlap, Chunk 2 would ALSO contain the end of Chunk 1:

    Chunk 1: "...NVIDIA reported total revenue of"
    Chunk 2: "NVIDIA reported total revenue of $60.9 billion, a 126% increase..."

This way, the important sentence exists in at least one complete chunk.

WHAT YOU'LL LEARN:
- Sliding window technique (used everywhere in NLP)
- Why metadata on chunks is essential for retrieval
- Trade-offs in chunk size selection
"""

from dataclasses import dataclass, field

from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Chunk:
    """
    A single chunk of text with metadata.

    This is the ATOMIC UNIT of our RAG system.
    When a user asks "What are NVIDIA's risks in 2024?",
    we search for chunks where:
        company="nvidia" AND year="2024" AND the text is relevant.
    """
    chunk_id: str              # Unique identifier (company_year_chunkN)
    text: str                  # The actual text content
    char_count: int = 0        # Number of characters

    # ── Metadata ──
    # This metadata travels with the chunk everywhere:
    # into the vector database, into search results, into LLM prompts.
    company: str = ""
    year: str = ""
    region: str = ""
    report_type: str = ""
    chunk_index: int = 0       # Position in the document (0, 1, 2, ...)
    start_char: int = 0        # Where this chunk starts in the full text
    end_char: int = 0          # Where this chunk ends in the full text

    def __post_init__(self) -> None:
        self.char_count = len(self.text)


@dataclass
class ChunkedDocument:
    """All chunks from a single document, with summary statistics."""
    file_name: str
    company: str
    year: str
    region: str
    report_type: str
    chunks: list[Chunk] = field(default_factory=list)
    total_chars: int = 0
    avg_chunk_size: float = 0

    def compute_stats(self) -> None:
        if self.chunks:
            self.total_chars = sum(c.char_count for c in self.chunks)
            self.avg_chunk_size = self.total_chars / len(self.chunks)


def chunk_text(
    text: str,
    company: str = "",
    year: str = "",
    region: str = "",
    report_type: str = "",
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> ChunkedDocument:
    """
    Split text into overlapping chunks using a sliding window.

    HOW THE SLIDING WINDOW WORKS:
    ─────────────────────────────
    Imagine the text as a long ribbon:

    |════════════════════════════════════════════════|
     ^^^^^^^^^^^^^^^^  Chunk 1 (0 to chunk_size)
              ^^^^^^^^^^^^^^^^  Chunk 2 (step to step+chunk_size)
                       ^^^^^^^^^^^^^^^^  Chunk 3
                                ^^^^^^^^^^^^^^^^  Chunk 4

    step = chunk_size - overlap

    The "window" slides forward by `step` characters each time,
    creating overlapping coverage.

    SMART BOUNDARY DETECTION:
    ─────────────────────────
    We don't just cut at exactly `chunk_size` characters.
    Instead, we look for the nearest paragraph break (\n\n) or
    sentence end (. or \n) near the boundary. This avoids
    splitting mid-sentence.

    Args:
        text:          Cleaned document text
        company:       Company name for metadata
        year:          Year for metadata
        region:        Region for metadata
        report_type:   Report type for metadata
        chunk_size:    Characters per chunk (default from config)
        chunk_overlap: Overlap between chunks (default from config)

    Returns:
        ChunkedDocument with all chunks and stats
    """
    # Use config defaults if not specified
    size = chunk_size or settings.chunk_size
    overlap = chunk_overlap or settings.chunk_overlap

    # Validate inputs
    if overlap >= size:
        logger.warning(f"Overlap ({overlap}) >= chunk_size ({size}). Setting overlap to size/5.")
        overlap = size // 5

    step = size - overlap  # How far to move the window each iteration

    chunks: list[Chunk] = []
    text_length = len(text)
    start = 0
    chunk_index = 0

    while start < text_length:
        # ── Determine chunk end ──
        end = min(start + size, text_length)

        # ── Smart boundary: find a natural break point ──
        # Only if we're not at the very end of the text
        if end < text_length:
            # Look for paragraph break (\n\n) in the last 20% of the chunk
            search_start = end - (size // 5)
            para_break = text.rfind("\n\n", search_start, end)
            if para_break != -1:
                end = para_break + 1  # Include one newline

            else:
                # Fall back to sentence boundary (period + space or newline)
                sentence_break = text.rfind(". ", search_start, end)
                if sentence_break != -1:
                    end = sentence_break + 2  # Include period and space
                else:
                    # Fall back to any newline
                    newline = text.rfind("\n", search_start, end)
                    if newline != -1:
                        end = newline + 1

        # ── Extract chunk text ──
        chunk_text_content = text[start:end].strip()

        # Skip empty or very short chunks
        if len(chunk_text_content) < 50:
            start += step
            continue

        # ── Create chunk with metadata ──
        chunk = Chunk(
            chunk_id=f"{company}_{year}_chunk{chunk_index:04d}",
            text=chunk_text_content,
            company=company,
            year=year,
            region=region,
            report_type=report_type,
            chunk_index=chunk_index,
            start_char=start,
            end_char=end,
        )
        chunks.append(chunk)
        chunk_index += 1

        # ── Move the window ──
        start += step

    # ── Build result ──
    result = ChunkedDocument(
        file_name=f"{company}_{year}_{report_type}",
        company=company,
        year=year,
        region=region,
        report_type=report_type,
        chunks=chunks,
    )
    result.compute_stats()

    logger.info(
        f"   📦 Chunked into {len(chunks)} chunks "
        f"(avg {result.avg_chunk_size:.0f} chars, "
        f"size={size}, overlap={overlap})"
    )

    return result


# ──────────────────────────────────────────────
# 🧪 TEST: Run directly to see chunking in action
# ──────────────────────────────────────────────
if __name__ == "__main__":
    from backend.core.config import settings
    from backend.pipelines.pdf_extractor import extract_pdf
    from backend.pipelines.text_cleaner import clean_document_text

    print("\n" + "=" * 60)
    print("🧪 CHUNKING TEST")
    print("=" * 60)

    # Test on one PDF
    test_pdf = next(settings.data_dir.rglob("*.pdf"), None)
    if test_pdf:
        # Step 1: Extract
        doc = extract_pdf(test_pdf)

        if doc.extraction_success:
            # Step 2: Clean
            cleaned, _ = clean_document_text(
                doc.full_text, company=doc.company, year=doc.year
            )

            # Step 3: Chunk
            chunked = chunk_text(
                cleaned,
                company=doc.company,
                year=doc.year,
                region=doc.region,
                report_type=doc.report_type,
            )

            # Show results
            print(f"\n📊 Chunking Results for: {chunked.file_name}")
            print(f"   Total chunks: {len(chunked.chunks)}")
            print(f"   Avg chunk size: {chunked.avg_chunk_size:.0f} chars")

            # Show first 3 chunks
            for i, chunk in enumerate(chunked.chunks[:3]):
                print(f"\n{'─' * 50}")
                print(f"📦 Chunk {i} ({chunk.chunk_id})")
                print(f"   Chars: {chunk.char_count}")
                print(f"   Position: {chunk.start_char}–{chunk.end_char}")
                print(f"   Text preview: {chunk.text[:200]}...")
    else:
        print("No PDFs found!")

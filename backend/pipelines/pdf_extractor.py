"""
🧠 FinRAG — PDF Text Extractor
=================================

WHAT THIS DOES:
---------------
Extracts text from financial report PDFs, page by page.

WHY PyMuPDF (fitz)?
-------------------
We chose PyMuPDF over alternatives because:

| Library      | Speed    | Table handling | Install |
|-------------|----------|----------------|---------|
| PyMuPDF     | ⚡ Fast  | Basic          | Easy    |
| pdfplumber  | 🐢 Slow  | ✅ Good        | Easy    |
| PyPDF2      | Medium   | ❌ Poor        | Easy    |
| Tika        | Medium   | ✅ Good        | Needs Java |

For Phase 1, PyMuPDF is perfect — fast extraction with good accuracy.
We can add pdfplumber later specifically for table extraction if needed.

WHAT YOU'LL LEARN:
- Working with binary file formats (PDFs are NOT plain text)
- Page-by-page extraction strategy
- Metadata extraction from file names
- Error handling for corrupt/encrypted PDFs

CHALLENGES TO EXPECT:
1. Some pages are scanned images → no text extracted (OCR needed)
2. Tables come out as garbled text → columns lose alignment
3. Headers/footers repeat on every page → noise in our data
4. Financial symbols (₹, €, §) may have encoding issues
"""

from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF — imported as 'fitz' (historical naming)

from backend.core.logging import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# 📦 DATA CLASSES
# ──────────────────────────────────────────────
# We use dataclasses to structure our extracted data.
# WHY? Because passing around raw dicts leads to bugs —
# you forget what keys exist, make typos, etc.
# Dataclasses give us type safety + autocomplete.


@dataclass
class PageContent:
    """Represents extracted content from a single PDF page."""
    page_number: int          # 1-indexed (humans count from 1)
    text: str                 # Raw text from this page
    char_count: int = 0       # How many characters extracted
    has_content: bool = True  # False if page was blank/image-only

    def __post_init__(self) -> None:
        """Auto-compute char_count after initialization."""
        self.char_count = len(self.text.strip())
        self.has_content = self.char_count > 50  # Less than 50 chars = likely empty


@dataclass
class ExtractedDocument:
    """
    Complete extraction result for one PDF.

    This is the OUTPUT of our extractor — everything downstream
    (cleaning, chunking, embedding) will consume this.
    """
    file_path: Path                          # Original PDF path
    file_name: str = ""                      # e.g., "nvidia_2024_annual.pdf"
    company: str = ""                        # e.g., "nvidia"
    year: str = ""                           # e.g., "2024"
    region: str = ""                         # e.g., "us" or "india"
    report_type: str = ""                    # e.g., "annual"
    total_pages: int = 0                     # Total page count
    pages: list[PageContent] = field(default_factory=list)
    full_text: str = ""                      # All pages combined
    extraction_success: bool = True          # Did extraction complete?
    error_message: str = ""                  # If failed, why?

    def __post_init__(self) -> None:
        """Auto-extract metadata from file path."""
        self.file_name = self.file_path.name
        self._extract_metadata_from_path()

    def _extract_metadata_from_path(self) -> None:
        """
        Extract company, year, region from file path structure.

        Your files follow this pattern:
            data/india/annual/reliance/reliance_2024_annual.pdf
            data/us/annual/nvidia/nvidia_2024_annual.pdf

        We parse the PATH to get metadata — this is more reliable
        than trying to extract it from the PDF content itself.

        WHY THIS MATTERS:
        Later, when we store chunks in the database, each chunk needs
        metadata like company and year. This is how we enable queries like
        "Show me all risks from NVIDIA 2024".
        """
        parts = self.file_path.parts
        # Find 'data' in path and extract relative structure
        try:
            # Path: .../data/region/report_type/company/filename
            data_idx = list(parts).index("data")
            if len(parts) > data_idx + 3:
                self.region = parts[data_idx + 1]           # "us" or "india"
                self.report_type = parts[data_idx + 2]      # "annual"
                self.company = parts[data_idx + 3]          # "nvidia"

            # Extract year from filename: nvidia_2024_annual.pdf → "2024"
            stem = self.file_path.stem  # filename without extension
            name_parts = stem.split("_")
            for part in name_parts:
                if part.isdigit() and len(part) == 4:
                    self.year = part
                    break
        except (ValueError, IndexError):
            logger.warning(f"Could not parse metadata from path: {self.file_path}")


# ──────────────────────────────────────────────
# 🔧 EXTRACTOR FUNCTION
# ──────────────────────────────────────────────

def extract_pdf(pdf_path: Path) -> ExtractedDocument:
    """
    Extract text from a single PDF file, page by page.

    This is the CORE function of our extraction pipeline.
    It opens the PDF, reads each page, and returns structured data.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        ExtractedDocument with all pages and metadata

    HOW PyMuPDF WORKS UNDER THE HOOD:
    1. Opens the PDF binary format
    2. For each page, finds text objects (not images)
    3. Reconstructs reading order (left→right, top→bottom)
    4. Returns Unicode text

    IMPORTANT LIMITATION:
    If a page is a SCANNED IMAGE (like a photographed document),
    PyMuPDF returns empty string. You'd need OCR (Tesseract) for that.
    Most modern annual reports are digital, so this is rarely an issue.
    """
    doc = ExtractedDocument(file_path=pdf_path)

    try:
        # ── Open the PDF ──
        # fitz.open() loads the entire PDF structure into memory.
        # For very large PDFs (500+ pages), this could use significant RAM.
        pdf = fitz.open(str(pdf_path))
        doc.total_pages = len(pdf)

        logger.info(
            f"📄 Extracting: {doc.file_name} "
            f"({doc.total_pages} pages) "
            f"[{doc.company}/{doc.year}]"
        )

        # ── Extract page by page ──
        all_text_parts: list[str] = []

        for page_num in range(doc.total_pages):
            page = pdf[page_num]

            # get_text("text") extracts plain text in reading order
            # Other options:
            #   "blocks" → paragraphs with position info
            #   "dict"   → full structure (fonts, sizes, colors)
            #   "html"   → formatted HTML output
            # We use "text" for simplicity in Phase 1.
            page_text = page.get_text("text")

            page_content = PageContent(
                page_number=page_num + 1,  # Convert 0-indexed → 1-indexed
                text=page_text,
            )
            doc.pages.append(page_content)

            if page_content.has_content:
                all_text_parts.append(page_text)

        # ── Combine all pages ──
        doc.full_text = "\n\n".join(all_text_parts)

        # ── Log extraction summary ──
        content_pages = sum(1 for p in doc.pages if p.has_content)
        empty_pages = doc.total_pages - content_pages
        total_chars = len(doc.full_text)

        logger.info(
            f"   ✅ Extracted {content_pages}/{doc.total_pages} pages "
            f"({empty_pages} empty) — {total_chars:,} chars"
        )

        if empty_pages > 0:
            # This is educational — shows you which pages had no text
            empty_page_nums = [p.page_number for p in doc.pages if not p.has_content]
            logger.info(f"   ⚠️  Empty pages (likely images/charts): {empty_page_nums}")

        pdf.close()

    except fitz.FileDataError:
        # ── PASSWORD PROTECTED or CORRUPTED PDF ──
        doc.extraction_success = False
        doc.error_message = "PDF is encrypted or corrupted"
        logger.error(f"   ❌ Failed: {doc.error_message} — {pdf_path.name}")

    except Exception as e:
        # ── UNEXPECTED ERROR ──
        doc.extraction_success = False
        doc.error_message = str(e)
        logger.error(f"   ❌ Failed: {e} — {pdf_path.name}")

    return doc


def extract_all_pdfs(data_dir: Path) -> list[ExtractedDocument]:
    """
    Extract text from ALL PDFs in the data directory.

    Scans recursively through all subdirectories:
        data/india/annual/*/
        data/us/annual/*/

    Returns a list of ExtractedDocument objects.
    """
    pdf_files = sorted(data_dir.rglob("*.pdf"))

    if not pdf_files:
        logger.warning(f"No PDF files found in {data_dir}")
        return []

    logger.info(f"🔍 Found {len(pdf_files)} PDFs to process")
    logger.info("=" * 60)

    results: list[ExtractedDocument] = []
    success_count = 0
    fail_count = 0

    for pdf_path in pdf_files:
        doc = extract_pdf(pdf_path)
        results.append(doc)

        if doc.extraction_success:
            success_count += 1
        else:
            fail_count += 1

    # ── Summary ──
    logger.info("=" * 60)
    logger.info(f"📊 Extraction complete: {success_count} succeeded, {fail_count} failed")

    total_chars = sum(len(d.full_text) for d in results)
    total_pages = sum(d.total_pages for d in results)
    logger.info(f"📊 Total: {total_pages:,} pages, {total_chars:,} characters")

    return results


# ──────────────────────────────────────────────
# 🧪 RUN DIRECTLY FOR TESTING
# ──────────────────────────────────────────────
if __name__ == "__main__":
    from backend.core.config import settings

    print("\n" + "=" * 60)
    print("🧪 PDF EXTRACTION TEST")
    print("=" * 60 + "\n")

    # Extract ALL PDFs
    documents = extract_all_pdfs(settings.data_dir)

    # Show a sample of what we extracted
    if documents:
        sample = documents[0]
        print(f"\n{'=' * 60}")
        print(f"📋 SAMPLE: {sample.file_name}")
        print(f"{'=' * 60}")
        print(f"Company:  {sample.company}")
        print(f"Year:     {sample.year}")
        print(f"Region:   {sample.region}")
        print(f"Pages:    {sample.total_pages}")
        print(f"Chars:    {len(sample.full_text):,}")
        print(f"\n--- First 500 chars of text ---")
        print(sample.full_text[:500])
        print("...")

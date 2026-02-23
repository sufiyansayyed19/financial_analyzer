"""
🧠 FinRAG — Table Extractor (PyMuPDF)
========================================

WHAT THIS DOES:
---------------
Extracts tables from financial PDFs as STRUCTURED DATA (rows + columns).

WHY PyMuPDF's find_tables() (and NOT pdfplumber):
---------------------------------------------------
We started with pdfplumber but it was too slow — 20+ minutes for 21 PDFs.

| Approach          | Speed     | Accuracy | Extra installs |
|-------------------|-----------|----------|----------------|
| pdfplumber        | 🐢 Very slow | Good     | None           |
| Camelot           | ⚡ Fast    | Best     | Ghostscript    |
| PyMuPDF find_tables() | ⚡ Fast | Good     | None (already have it!) |

PyMuPDF added find_tables() in v1.23. Since we already use PyMuPDF
for text extraction, this is the ZERO-OVERHEAD solution.

CHALLENGE #1:
    pdfplumber took 20+ minutes for 21 PDFs (5,350 pages).
    Users uploading dynamically can't wait that long.

SOLUTION #1:
    Switched to PyMuPDF's find_tables() — uses the same C library
    we already have. No extra dependencies needed.

CHALLENGE #2:
    Even PyMuPDF's find_tables() was slow on large PDFs (15+ min
    for JPMorgan's 350-page reports). The function was analyzing
    EVERY page, even narrative-only pages with zero tables.

SOLUTION #2:
    Added a fast PRE-CHECK before calling find_tables():
    → Count drawn lines/rectangles on the page first (instant)
    → Only call find_tables() if enough lines exist to form a table
    → Skips ~80% of pages → massive speed improvement

LESSON:
    The fastest code is the code that doesn't run.
    Pre-filtering is a fundamental optimization pattern.

WHAT YOU'LL LEARN:
- Table detection in PDFs (how lines → cells → rows → tables)
- Structured vs unstructured data handling
- Markdown table formatting for LLM context
- Real-world performance optimization decisions
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

from backend.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedTable:
    """A single table extracted from a PDF page."""
    table_index: int          # Which table overall (0, 1, 2...)
    page_number: int          # Which page it came from
    headers: list[str]        # Column headers (first row)
    rows: list[list[str]]     # Data rows
    row_count: int = 0
    col_count: int = 0
    markdown: str = ""        # Table as readable markdown

    def __post_init__(self) -> None:
        self.row_count = len(self.rows)
        self.col_count = len(self.headers) if self.headers else 0
        self.markdown = self._to_markdown()

    def _to_markdown(self) -> str:
        """
        Convert table to readable Markdown format.

        WHY MARKDOWN?
        → LLMs understand markdown tables extremely well.
        → When we build the RAG pipeline, we can feed table markdown
          directly into the LLM prompt as context.
        → Human-readable too — easy to inspect and debug.
        """
        if not self.headers:
            return ""

        # Clean headers — replace None/empty with placeholder
        clean_headers = [h.strip() if h and h.strip() else f"Col_{i}" for i, h in enumerate(self.headers)]

        # Build header row
        header_line = "| " + " | ".join(clean_headers) + " |"
        separator = "| " + " | ".join(["---"] * len(clean_headers)) + " |"

        # Build data rows
        data_lines = []
        for row in self.rows:
            padded_row = list(row) + [""] * (len(clean_headers) - len(row))
            clean_row = [cell.strip() if cell else "" for cell in padded_row[:len(clean_headers)]]
            data_lines.append("| " + " | ".join(clean_row) + " |")

        return "\n".join([header_line, separator] + data_lines)


@dataclass
class DocumentTables:
    """All tables from a single PDF document."""
    file_name: str
    company: str = ""
    year: str = ""
    tables: list[ExtractedTable] = field(default_factory=list)
    total_tables: int = 0
    pages_with_tables: int = 0

    def compute_stats(self) -> None:
        self.total_tables = len(self.tables)
        self.pages_with_tables = len(set(t.page_number for t in self.tables))


def _page_has_table_lines(page: fitz.Page, min_lines: int = 4) -> bool:
    """
    FAST pre-check: does this page have enough drawn lines to form a table?

    WHY THIS EXISTS (PERFORMANCE OPTIMIZATION):
    ─────────────────────────────────────────────
    find_tables() is EXPENSIVE — it analyzes page geometry to detect tables.
    But ~80% of pages in annual reports are narrative text with ZERO tables.

    This function checks for drawn line segments FIRST (instant operation).
    A table needs at LEAST 4 lines (2 horizontal + 2 vertical = 1 cell).
    If a page doesn't have enough lines, we skip find_tables() entirely.

    This reduced JPMorgan processing from 15+ minutes to ~1-2 minutes.

    Args:
        page: PyMuPDF page object
        min_lines: Minimum line segments needed (default 4)

    Returns:
        True if page likely has a table, False to skip
    """
    try:
        drawings = page.get_drawings()
        line_count = 0
        for d in drawings:
            for item in d.get("items", []):
                # Count lines and rectangles (table building blocks)
                if item[0] in ("l", "re"):  # "l" = line, "re" = rectangle
                    line_count += 1
                    if line_count >= min_lines:
                        return True  # Early exit — enough lines found
        return False
    except Exception:
        # If drawing detection fails, try find_tables anyway
        return True


def extract_tables_from_pdf(pdf_path: Path, company: str = "", year: str = "") -> DocumentTables:
    """
    Extract all tables from a PDF using PyMuPDF's find_tables().

    HOW find_tables() WORKS:
    ────────────────────────
    1. Scans each page for horizontal and vertical line segments
    2. Finds intersections → these form cell boundaries
    3. Groups cells into rows and columns
    4. Extracts text from each cell
    5. Returns structured table data

    PERFORMANCE OPTIMIZATION:
    Before calling find_tables() on each page, we run a fast pre-check
    (_page_has_table_lines) that counts drawn lines. Pages without enough
    lines to form a table are skipped entirely → ~5x speedup.

    QUALITY FILTERS WE APPLY:
    - Skip tables with < 2 rows (need at least header + 1 data row)
    - Skip tables where headers are all empty
    - Skip single-column "tables" (likely just a list, not a real table)
    - Clean cell text (remove excessive whitespace, newlines)
    """
    result = DocumentTables(
        file_name=pdf_path.name,
        company=company,
        year=year,
    )

    try:
        pdf = fitz.open(str(pdf_path))

        logger.info(f"📊 Extracting tables: {pdf_path.name} ({len(pdf)} pages)")

        table_count = 0
        pages_skipped = 0
        page_num = 0
        total_pages = len(pdf)

        while page_num < total_pages:
            try:
                page = pdf[page_num]

                # ── FAST PRE-CHECK: skip pages without table-like drawings ──
                if not _page_has_table_lines(page):
                    pages_skipped += 1
                    page_num += 1
                    continue

                # find_tables() — only runs on pages that likely have tables
                tables = page.find_tables()

                if tables and tables.tables:
                    for table in tables.tables:
                        # Extract the table data as a list of lists
                        table_data = table.extract()

                        # ── QUALITY FILTER ──
                        if not table_data or len(table_data) < 2:
                            continue  # Need header + at least 1 data row

                        # Clean cell values: replace None, strip whitespace, fix newlines
                        cleaned_data = []
                        for row in table_data:
                            cleaned_row = []
                            for cell in row:
                                if cell is None:
                                    cleaned_row.append("")
                                else:
                                    # Replace internal newlines with space, strip whitespace
                                    cleaned_row.append(str(cell).replace("\n", " ").strip())
                            cleaned_data.append(cleaned_row)

                        headers = cleaned_data[0]
                        rows = cleaned_data[1:]

                        # Skip if all headers are empty
                        if not any(h for h in headers if h.strip()):
                            continue

                        # Skip single-column "tables" (not real tables)
                        non_empty_cols = sum(1 for h in headers if h.strip())
                        if non_empty_cols < 2:
                            continue

                        # ── CREATE TABLE OBJECT ──
                        extracted = ExtractedTable(
                            table_index=table_count,
                            page_number=page_num + 1,  # 1-indexed
                            headers=headers,
                            rows=rows,
                        )

                        result.tables.append(extracted)
                        table_count += 1

                page_num += 1

            except Exception as e:
                logger.warning(f"   ⚠️ Error extracting tables on page {page_num+1}: {e}")
                
                # If PyMuPDF suffers a severe internal crash, it closes the document object.
                # We need to reopen it to continue processing the rest of the pages.
                if "document closed" in str(e).lower() or "closed" in str(e).lower():
                    logger.warning(f"   🔄 Reopening PDF to recover from crash...")
                    try:
                        pdf = fitz.open(str(pdf_path))
                    except Exception as reopen_err:
                        logger.error(f"   ❌ Could not reopen PDF, aborting table extraction: {reopen_err}")
                        break
                
                page_num += 1

        if not pdf.is_closed:
            pdf.close()
        result.compute_stats()

        logger.info(
            f"   📊 Found {result.total_tables} tables "
            f"across {result.pages_with_tables} pages "
            f"(skipped {pages_skipped}/{len(pdf)} pages — no table lines)"
        )

    except Exception as e:
        logger.error(f"   ❌ Table extraction failed: {e}")

    return result


def save_tables(doc_tables: DocumentTables, output_dir: Path) -> Path | None:
    """
    Save extracted tables as JSON + combined markdown.

    Two output files per document:
    - _tables.json  → structured data for database loading later
    - _tables.md    → readable markdown for LLM context and human review
    """
    if not doc_tables.tables:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = Path(doc_tables.file_name).stem

    # ── Save JSON (structured) ──
    json_data = {
        "metadata": {
            "company": doc_tables.company,
            "year": doc_tables.year,
            "total_tables": doc_tables.total_tables,
            "source_file": doc_tables.file_name,
        },
        "tables": [
            {
                "table_index": t.table_index,
                "page_number": t.page_number,
                "headers": t.headers,
                "rows": t.rows,
                "row_count": t.row_count,
                "col_count": t.col_count,
            }
            for t in doc_tables.tables
        ],
    }

    json_path = output_dir / f"{base_name}_tables.json"
    json_path.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Save Markdown (readable) ──
    md_parts = [f"# Tables from {doc_tables.file_name}\n"]
    for table in doc_tables.tables:
        md_parts.append(f"\n## Table {table.table_index + 1} (Page {table.page_number})\n")
        md_parts.append(table.markdown)
        md_parts.append("")

    md_path = output_dir / f"{base_name}_tables.md"
    md_path.write_text("\n".join(md_parts), encoding="utf-8")

    logger.info(f"   💾 Saved: {json_path.name} + {md_path.name}")
    return output_dir


# ──────────────────────────────────────────────
# 🧪 TEST: Run on one PDF to see tables
# ──────────────────────────────────────────────
if __name__ == "__main__":
    from backend.core.config import settings

    print("\n" + "=" * 60)
    print("🧪 TABLE EXTRACTION TEST (PyMuPDF)")
    print("=" * 60)

    # Test on NVIDIA PDF (smaller, faster)
    test_pdf = next(settings.data_dir.rglob("nvidia_2024*"), None)
    if not test_pdf:
        test_pdf = next(settings.data_dir.rglob("*.pdf"), None)

    if test_pdf:
        doc_tables = extract_tables_from_pdf(test_pdf, company="nvidia", year="2024")

        print(f"\n📊 Found {doc_tables.total_tables} tables")

        # Show first 3 tables
        for table in doc_tables.tables[:3]:
            print(f"\n{'─' * 60}")
            print(f"Table {table.table_index + 1} (Page {table.page_number}) — {table.row_count} rows × {table.col_count} cols")
            print(table.markdown[:500])
    else:
        print("No PDFs found!")

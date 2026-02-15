"""
🧠 FinRAG — Text Cleaner
==========================

WHAT THIS DOES:
---------------
Cleans raw PDF-extracted text into usable, consistent format.

WHY CLEANING IS CRITICAL:
--------------------------
Raw PDF text is MESSY. Here's what financial PDFs throw at us:

1. REPEATED HEADERS/FOOTERS:
   "NVIDIA Corporation Annual Report 2024" appears on every page.
   If we don't remove these, our chunks will be full of noise.

2. EXCESSIVE WHITESPACE:
   PDF extraction often produces:
   - Multiple blank lines between paragraphs
   - Irregular spacing within lines
   - Tab characters mixed with spaces

3. PAGE NUMBERS:
   "Page 42 of 300" or just "42" appearing as standalone lines.

4. SPECIAL CHARACTERS:
   - Unicode noise: \x00, \xa0 (non-breaking space)
   - Financial symbols: ₹, €, £ (we KEEP these — they're meaningful)
   - Bullet points: •, ●, ▪ → normalize to standard format

5. LINE BREAK ISSUES:
   PDFs often break words across lines:
   "The com-
   pany reported"
   We need to rejoin these.

WHAT YOU'LL LEARN:
- Regular expressions (regex) for text processing
- Why cleaning is 80% of real-world NLP work
- The difference between "noise" and "signal" in text data
"""

import re
from dataclasses import dataclass

from backend.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CleaningStats:
    """Track what the cleaner changed — useful for debugging."""
    original_chars: int = 0
    cleaned_chars: int = 0
    lines_removed: int = 0
    whitespace_normalized: int = 0

    @property
    def reduction_percent(self) -> float:
        """How much text was removed as noise."""
        if self.original_chars == 0:
            return 0.0
        return (1 - self.cleaned_chars / self.original_chars) * 100


def clean_text(raw_text: str, company: str = "", year: str = "") -> tuple[str, CleaningStats]:
    """
    Clean raw extracted text from a financial PDF.

    This function applies a SEQUENCE of cleaning steps.
    ORDER MATTERS — each step builds on the previous one.

    Args:
        raw_text:  Raw text from PyMuPDF extraction
        company:   Company name (used to detect repeated headers)
        year:      Report year (used to detect repeated headers)

    Returns:
        Tuple of (cleaned_text, stats)

    WHY return stats?
    → So we can log how much was cleaned. If cleaning removes 90%
      of text, something might be wrong with our rules.
    """
    stats = CleaningStats(original_chars=len(raw_text))

    text = raw_text

    # ──────────────────────────────────────────
    # STEP 1: Replace problematic Unicode
    # ──────────────────────────────────────────
    # \xa0 = non-breaking space (very common in PDFs)
    # \x00 = null byte (corrupted text)
    # \xad = soft hyphen (invisible character)
    text = text.replace("\xa0", " ")
    text = text.replace("\x00", "")
    text = text.replace("\xad", "")

    # ──────────────────────────────────────────
    # STEP 2: Normalize line endings
    # ──────────────────────────────────────────
    # PDFs may use \r\n (Windows) or \r (old Mac) or \n (Unix)
    # Standardize to \n
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # ──────────────────────────────────────────
    # STEP 3: Fix hyphenated line breaks
    # ──────────────────────────────────────────
    # Financial reports often break words across lines:
    #   "The com-\npany reported strong growth"
    #   → "The company reported strong growth"
    #
    # REGEX EXPLAINED:
    #   (\w)   = capture a word character (letter/digit)
    #   -      = literal hyphen
    #   \s*\n  = optional whitespace then newline
    #   \s*    = optional whitespace on next line
    #   (\w)   = capture first word character of next line
    #
    # \1\2 = join the two captured characters
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)

    # ──────────────────────────────────────────
    # STEP 4: Remove page numbers
    # ──────────────────────────────────────────
    # Common patterns:
    #   "42"  (standalone number on a line)
    #   "Page 42"
    #   "Page 42 of 300"
    #   "- 42 -"
    #
    # REGEX EXPLAINED:
    #   ^       = start of line
    #   \s*     = optional whitespace
    #   [-–—]*  = optional dashes
    #   \s*     = optional whitespace
    #   (page\s*)? = optional word "page"
    #   \d{1,4} = 1-4 digit number
    #   (\s*of\s*\d+)? = optional "of N"
    #   \s*[-–—]* = optional trailing dashes
    #   \s*$    = end of line
    text = re.sub(
        r"^\s*[-–—]*\s*(?:page\s*)?\d{1,4}(?:\s*of\s*\d+)?\s*[-–—]*\s*$",
        "",
        text,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    # ──────────────────────────────────────────
    # STEP 5: Remove repeated headers/footers
    # ──────────────────────────────────────────
    # Annual reports repeat company name + year on every page.
    # We build dynamic patterns based on the company and year.
    if company:
        # Remove lines that are JUST the company name
        # (case-insensitive, with optional surrounding noise)
        escaped_company = re.escape(company)
        text = re.sub(
            rf"^\s*{escaped_company}.*(?:annual|report|corporation|limited|ltd|inc).*$",
            "",
            text,
            flags=re.MULTILINE | re.IGNORECASE,
        )

    if year:
        # Remove lines that are JUST the year
        text = re.sub(
            rf"^\s*{re.escape(year)}\s*$",
            "",
            text,
            flags=re.MULTILINE,
        )

    # ──────────────────────────────────────────
    # STEP 6: Normalize bullet points
    # ──────────────────────────────────────────
    # PDFs use various bullet characters. Standardize to "•"
    text = re.sub(r"[●▪▸►◆◇○]", "•", text)

    # ──────────────────────────────────────────
    # STEP 7: Normalize whitespace
    # ──────────────────────────────────────────
    # Replace multiple spaces/tabs within a line with single space
    text = re.sub(r"[ \t]+", " ", text)

    # Replace 3+ consecutive newlines with exactly 2
    # (preserve paragraph breaks but remove excessive gaps)
    prev_len = len(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    stats.whitespace_normalized = prev_len - len(text)

    # ──────────────────────────────────────────
    # STEP 8: Remove very short lines (likely noise)
    # ──────────────────────────────────────────
    # Lines with fewer than 3 characters are usually artifacts
    # (stray numbers, bullet points, etc.)
    lines = text.split("\n")
    original_line_count = len(lines)
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()
        # Keep the line if:
        # - It has 3+ characters, OR
        # - It's empty (preserves paragraph breaks)
        if len(stripped) >= 3 or stripped == "":
            cleaned_lines.append(line)

    stats.lines_removed = original_line_count - len(cleaned_lines)
    text = "\n".join(cleaned_lines)

    # ──────────────────────────────────────────
    # STEP 9: Final trim
    # ──────────────────────────────────────────
    text = text.strip()

    stats.cleaned_chars = len(text)

    return text, stats


def clean_document_text(full_text: str, company: str = "", year: str = "") -> tuple[str, CleaningStats]:
    """
    Clean the full text of a document.

    This is just a wrapper that adds logging around clean_text.
    In a real system, you might add document-specific rules here.
    """
    cleaned, stats = clean_text(full_text, company=company, year=year)

    logger.info(
        f"   🧹 Cleaned: {stats.original_chars:,} → {stats.cleaned_chars:,} chars "
        f"({stats.reduction_percent:.1f}% reduced, {stats.lines_removed} lines removed)"
    )

    return cleaned, stats


# ──────────────────────────────────────────────
# 🧪 TEST: Run directly to see cleaning in action
# ──────────────────────────────────────────────
if __name__ == "__main__":
    from backend.core.config import settings
    from backend.pipelines.pdf_extractor import extract_pdf

    print("\n" + "=" * 60)
    print("🧪 TEXT CLEANING TEST")
    print("=" * 60)

    # Test on one PDF
    test_pdf = next(settings.data_dir.rglob("*.pdf"), None)
    if test_pdf:
        doc = extract_pdf(test_pdf)
        if doc.extraction_success:
            cleaned, stats = clean_document_text(
                doc.full_text,
                company=doc.company,
                year=doc.year,
            )

            print(f"\n📊 Cleaning Stats:")
            print(f"   Original:   {stats.original_chars:,} chars")
            print(f"   Cleaned:    {stats.cleaned_chars:,} chars")
            print(f"   Reduction:  {stats.reduction_percent:.1f}%")
            print(f"   Lines removed: {stats.lines_removed}")

            print(f"\n--- First 500 chars of CLEANED text ---")
            print(cleaned[:500])
            print("...")
    else:
        print("No PDFs found!")

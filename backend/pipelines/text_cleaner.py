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

    # ── STEP 1b: Resolve typographic ligatures ──
    # PDFs embed ligature characters like ﬁ (U+FB01) instead of "fi".
    # These look fine visually but break text search and NLP:
    #   "ﬁnancial" won't match "financial" in search!
    # TCS reports had 100+ of these per file.
    ligature_map = {
        "\ufb00": "ff",   # ﬀ
        "\ufb01": "fi",   # ﬁ
        "\ufb02": "fl",   # ﬂ
        "\ufb03": "ffi",  # ﬃ
        "\ufb04": "ffl",  # ﬄ
    }
    for lig, replacement in ligature_map.items():
        text = text.replace(lig, replacement)

    # ── STEP 1c: Remove control characters ──
    # Some PDFs contain invisible control chars (ASCII 0-31)
    # that corrupt downstream processing. Keep only \n, \r, \t.
    # Reliance reports had 1000+ of these.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

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

    # ── STEP 5b: Auto-detect and remove repeated lines ──
    # Financial PDFs repeat section headers on EVERY page:
    #   "Financial Statements" → 206 times in HDFC Bank
    #   "JPMorgan Chase & Co./2022 Form 10-K" → 261 times
    #
    # Instead of hardcoding patterns, we COUNT line frequencies
    # and remove any line appearing 8+ times (clearly a header/footer).
    #
    # WHY 8? Most real content appears 1-3 times. Headers appear
    # on most pages (100-300+). 8 is a safe threshold that catches
    # headers without removing legitimate repeated financial terms.
    from collections import Counter
    line_freq = Counter()
    temp_lines = text.split("\n")
    for line in temp_lines:
        stripped = line.strip()
        if len(stripped) > 10:  # Only track substantial lines
            line_freq[stripped] += 1

    # Build set of lines to remove (appearing 8+ times)
    repeated_lines = {line for line, count in line_freq.items() if count >= 8}

    if repeated_lines:
        cleaned = []
        removed_count = 0
        for line in temp_lines:
            if line.strip() in repeated_lines:
                cleaned.append("")  # Replace with blank (collapsed later)
                removed_count += 1
            else:
                cleaned.append(line)
        text = "\n".join(cleaned)
        stats.lines_removed += removed_count

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

    # Replace 3+ consecutive blank/whitespace-only lines with exactly 2 newlines
    # (preserve paragraph breaks but remove excessive gaps)
    #
    # IMPORTANT: We use (\s*\n) not just (\n) because PDF extraction
    # often produces lines with ONLY spaces/tabs — these look blank
    # but the regex \n{3,} won't catch them!
    prev_len = len(text)
    text = re.sub(r"(\s*\n){3,}", "\n\n", text)
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
    # STEP 8.5: Collapse blank lines AGAIN
    # ──────────────────────────────────────────
    # WHY AGAIN? Step 8 removed short lines, which created NEW
    # consecutive blank line runs. For example:
    #   [blank] + [removed "42"] + [blank] → [blank][blank][blank]
    #
    # LESSON: When pipeline steps create side effects, you sometimes
    # need a "cleanup" pass at the end.
    text = re.sub(r"(\s*\n){3,}", "\n\n", text)

    # Strip trailing whitespace from each line
    text = "\n".join(line.rstrip() for line in text.split("\n"))

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

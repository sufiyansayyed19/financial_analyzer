# 📓 Phase 1 Learning Journal — Foundation & PDF Ingestion

**Date:** February 15–16, 2026  
**Duration:** ~3 hours  
**Result:** ✅ 21 PDFs → 24,948 text chunks + 20 PDFs with structured table extraction

---

## 🗂️ Files Created (in order)

| # | File | Purpose |
|---|------|---------|
| 1 | `requirements.txt` | Dependencies: PyMuPDF, FastAPI, Pydantic, Rich |
| 2 | `backend/__init__.py` | Makes `backend/` a Python package |
| 3 | `backend/core/__init__.py` | Core module package init |
| 4 | `backend/core/config.py` | Centralized settings using Pydantic BaseSettings |
| 5 | `backend/core/logging.py` | Structured logging with Rich handler |
| 6 | `backend/pipelines/__init__.py` | Pipelines module package init |
| 7 | `backend/api/__init__.py` | API module placeholder (Phase 5) |
| 8 | `backend/services/__init__.py` | Services placeholder (Phase 3+) |
| 9 | `backend/engines/__init__.py` | Engines placeholder (Phase 2+) |
| 10 | `backend/workers/__init__.py` | Workers placeholder (Phase 6) |
| 11 | `backend/llm/__init__.py` | LLM module placeholder (Phase 3) |
| 12 | `backend/db/__init__.py` | Database placeholder (Phase 2) |
| 13 | `.env` | Environment variables for local dev |
| 14 | `backend/main.py` | Entry point — validates project setup |
| 15 | `backend/pipelines/pdf_extractor.py` | PDF text extraction with PyMuPDF |
| 16 | `backend/pipelines/text_cleaner.py` | Multi-step text cleaning pipeline |
| 17 | `backend/pipelines/chunker.py` | Sliding window chunking with smart boundaries |
| 18 | `backend/pipelines/ingest.py` | End-to-end orchestration pipeline |
| 19 | `backend/pipelines/table_extractor.py` | Structured table extraction from PDFs |

---

## 🧠 Key Concepts Learned

### 1. Pydantic BaseSettings (config.py)
**What:** A config class that reads values from `.env` file → environment variables → defaults.  
**Why it matters:** In production, you NEVER hardcode paths or secrets. BaseSettings lets you change behavior without changing code — just update `.env`.  
**Pattern:** Singleton — one `settings` object shared everywhere via `from backend.core.config import settings`.

### 2. Python Packages (`__init__.py`)
**What:** An empty `__init__.py` file makes a folder importable as a Python module.  
**Why it matters:** Without it, `from backend.core.config import settings` would fail — Python wouldn't recognize `backend/` as a package.

### 3. `pathlib.Path` vs string paths
**What:** Modern Python way to handle file paths.  
**Why it matters:** Works cross-platform (Windows `\` vs Linux `/`). Supports operations like `.rglob("*.pdf")` to find all PDFs recursively.

### 4. Dataclasses for structured data
**What:** `@dataclass` auto-generates `__init__`, `__repr__`, etc.  
**Why it matters:** Passing raw dicts leads to bugs (typos in keys, missing fields). Dataclasses give type safety and IDE autocomplete.

### 5. PyMuPDF (fitz) for PDF extraction
**What:** Fast C-based library for reading PDFs. Imported as `fitz` (historical name).  
**Why it matters:** Handles both text extraction AND table detection (via `find_tables()`). Much faster than pdfplumber. Limitation: can't read scanned images (needs OCR).

### 6. Regex for text cleaning
**What:** Regular expressions — pattern matching language for text.  
**Key patterns used:**
- `r"(\w)-\s*\n\s*(\w)"` → fix hyphenated line breaks
- `r"^\\s*\\d{1,4}\\s*$"` → remove standalone page numbers
- `r"(\s*\n){3,}"` → collapse excessive blank lines (including whitespace-only lines)
- `r"[\x00-\x08\x0b\x0c\x0e-\x1f]"` → remove invisible control characters

**Key learning:** The regex `\n{3,}` only matches truly empty lines. PDF text often has lines with invisible spaces/tabs that look blank but aren't caught. Using `(\s*\n){3,}` catches both.

### 7. Typographic Ligatures
**What:** PDF fonts embed special characters like `ﬁ` (U+FB01) instead of "fi".  
**Problem:** "ﬁnancial" won't match "financial" in search or embeddings!  
**Fix:** Map ligatures to ASCII: `ﬁ→fi`, `ﬂ→fl`, `ﬀ→ff`, `ﬃ→ffi`, `ﬄ→ffl`.  
**Found in practice:** TCS reports had 100+ unresolved ligatures per file.

### 8. Sliding Window Chunking
**What:** Split text using a window that moves `step = chunk_size - overlap` characters each time.  
**Why overlap:** Prevents losing context at chunk boundaries. A sentence split across two chunks will be complete in at least one.  
**Smart boundaries:** Instead of cutting at exact character count, we find the nearest paragraph or sentence break.

### 9. Pipeline Orchestration Pattern
**What:** Each component (extract, clean, chunk, table_extract) is independent. A separate orchestrator (`ingest.py`) connects them.  
**Why it matters:** You can reuse any component alone. You can swap the extractor without touching the cleaner. This is "separation of concerns".

### 10. Optional Pipeline Steps with CLI Flags
**What:** The `--tables` flag on the ingest pipeline makes table extraction optional.  
**Why:** Text extraction takes ~35 seconds for all 21 PDFs. Table extraction adds minutes. For batch re-processing, text-only is fast. For single file uploads, tables are always included.  
**Pattern:** `argparse` for CLI flags → passed as boolean to the pipeline function.

---

## ⚡ Challenges Faced & Solutions

### Challenge #1: Rich markup crashes in PowerShell piping
**What happened:** Log messages with `[bold green]` markup caused errors when output was piped (`|`).  
**Root cause:** Rich interprets `[bold]` as formatting commands, but piped output doesn't support terminal formatting.  
**Fix:** Set `markup=False` in `RichHandler` configuration.  
**Lesson:** Terminal libraries behave differently in interactive vs piped mode.

### Challenge #2: Financial PDFs have messy extracted text
**What happened:** Raw text from PyMuPDF had repeated headers, page numbers, non-breaking spaces, hyphenated breaks, and garbled table columns.  
**Fix:** Built a multi-step sequential cleaner. Order matters — Unicode normalization comes before regex matching.  
**Lesson:** Text cleaning is 80% of real NLP work. Raw data is NEVER clean.

### Challenge #3: pdfplumber was too slow for table extraction
**What happened:** First attempt at table extraction used pdfplumber — took 20+ minutes for 21 PDFs (5,350 pages). Completely impractical for dynamic user uploads.  
**Fix:** Switched to PyMuPDF's built-in `find_tables()` — same library we already had, zero new dependencies.  
**Lesson:** Sometimes the best tool is the one you already have. Don't add dependencies when your existing tools can do the job.

### Challenge #4: PyMuPDF find_tables() slow on large PDFs
**What happened:** Even after switching from pdfplumber, JPMorgan's 350-page reports took 15+ minutes. `find_tables()` was analyzing _every_ page, even narrative-only pages.  
**Root cause:** The bottleneck was in PyMuPDF's internal `JM_rects_overlap` function — rectangle intersection detection on complex pages with many drawn elements.  
**Fix:** Added `_page_has_table_lines()` pre-check that counts drawn line segments BEFORE calling `find_tables()`. Pages without enough lines (min 4 for a 1-cell table) are skipped instantly. This eliminates ~80% of unnecessary work.  
**Result:** JPMorgan 2024 went from hanging indefinitely → completed in 57 seconds.  
**Lesson:** The fastest code is the code that doesn't run. Pre-filtering is a fundamental optimization pattern.

### Challenge #5: Deciding chunk size
**What happened:** Too small = loses context, too large = includes irrelevant info.  
**Decision:** 1000 chars with 200 overlap.  
**Result:** Average chunk ~932 chars — captures a complete paragraph or idea.  
**Lesson:** There's no universally "right" chunk size. It depends on content and retrieval needs.

### Challenge #6: Avoiding mid-sentence cuts in chunks
**What happened:** Fixed-size chunks would split sentences: "revenue of" | "$60.9 billion".  
**Fix:** Smart boundary detection — look for `\n\n` (paragraph) > `. ` (sentence) > `\n` (line) in the last 20% of each chunk.  
**Lesson:** Small details like this significantly impact RAG quality.

### Challenge #7: Excessive blank lines in cleaned text
**What happened:** Some files had 82 consecutive blank lines (Reliance 2023), 69 (TCS 2025).  
**Root cause:** The regex `\n{3,}` only matches truly empty lines. PDF extraction produces lines with invisible spaces/tabs that LOOK blank but have whitespace characters.  
**Fix:** Changed to `(\s*\n){3,}` which matches whitespace-only lines too. Applied TWICE — once in Step 7 and again in Step 8.5 (because Step 8's short-line removal creates new blank runs).  
**Result:** All 21 files went from max_consec=82 to max_consec=1.  
**Lesson:** When pipeline steps create side effects, you sometimes need a cleanup pass at the end.

### Challenge #8: Repeated headers appearing 200-300x per file
**What happened:** Quality audit revealed "HDFC Bank Limited" appeared 302 times, "JPMorgan Chase & Co./2022 Form 10-K" appeared 261 times. These are page headers/section markers repeated on every page.  
**Problem:** The existing company/year regex only caught simple patterns. Section headers like "Financial Statements" and "Statutory Reports" slipped through.  
**Fix:** Smart auto-detection — count line frequencies using `Counter`, then remove any line appearing 8+ times. Why 8? Real content appears 1-3 times; headers appear 100-300+ times. 8 is a safe threshold.  
**Result:** Went from all 21 files flagged → 19/21 fully clean.  
**Lesson:** Data-driven cleaning (let the data tell you what's noise) beats hardcoded rules.

### Challenge #9: Unresolved typographic ligatures
**What happened:** TCS PDFs had 100+ `ﬁ` characters. "ﬁnancial" won't match "financial" in embeddings or search.  
**Fix:** Ligature replacement map in Step 1b of the cleaner.  
**Lesson:** PDF fonts do surprising things invisible to the human eye. Always audit character-level quality.

### Challenge #10: Control characters in text
**What happened:** Reliance reports had 1,197 invisible control characters (ASCII 0-31).  
**Fix:** Regex strips all control chars except `\n`, `\r`, `\t`.  
**Lesson:** "Clean looking" text isn't necessarily "clean" — you need programmatic audits.

---

## 📊 Pipeline Results

### Text Pipeline: 21 PDFs → 24,948 chunks in ~35 seconds

| Company | Region | Reports | Total Pages | Total Chunks |
|---------|--------|---------|-------------|--------------|
| HDFC Bank | India | 3 (2022-2024) | 1,458 | 5,358 |
| Reliance | India | 3 (2023-2025) | 573 | 4,262 |
| TCS | India | 3 (2023-2025) | 1,022 | 3,902 |
| JPMorgan | US | 3 (2022-2024) | 1,064 | 5,039 |
| NVIDIA | US | 3 (2023-2025) | 537 | 2,377 |
| Pfizer | US | 3 (2022-2024) | 402 | 2,567 |
| Walmart | US | 3 (2023-2025) | 294 | 1,443 |

### Table Pipeline: 20/21 PDFs extracted (JPMorgan 2023 skipped — hangs in PyMuPDF)

**Output per PDF (4 files each):**
```
nvidia_2024_annual.txt          ← cleaned text
nvidia_2024_annual_chunks.json  ← text chunks with metadata
nvidia_2024_annual_tables.json  ← structured tables (headers + rows)
nvidia_2024_annual_tables.md    ← readable markdown tables for LLM context
```

### Text Quality Audit (13 checks per file):

| Check | Status |
|-------|--------|
| Control characters | ✅ All removed |
| Ligatures (fi/fl/ff) | ✅ All resolved |
| Repeated headers/footers | ✅ Auto-detected and removed |
| Consecutive blank lines | ✅ Max 1 (was up to 82) |
| Broken hyphenated words | ✅ 0 remaining |
| Single-char line noise | ✅ 0 remaining |
| Encoding artifacts (mojibake) | ✅ None found |
| CID font references | ✅ None found |
| Overall | **19/21 fully clean, 2 with trivial flags** |

---

## 🏗️ Architecture Decisions Made

1. **Pydantic BaseSettings** over plain dicts → type safety, `.env` support
2. **PyMuPDF** for both text AND tables → one library, zero overhead
3. **Dataclasses** over raw dicts → structured, type-safe data passing
4. **Metadata from file paths** over PDF content parsing → more reliable
5. **4 output files per PDF** → each serves a different consumer (see "Why 4 Output Files?" below)
6. **Idempotent pipeline** → safe to re-run without duplicates
7. **Optional table extraction** via `--tables` flag → fast batch (35s) vs comprehensive
8. **Data-driven header removal** (frequency counting) over hardcoded regex → catches all headers without manual patterns
9. **Pre-check heuristic** for table detection → skips 80% of pages, massive speedup
10. **Mirror directory structure** → `processed/` mirrors `data/` layout (see "Why This Directory Structure?" below)

---

## 🔬 Text Cleaning Pipeline (Final: 10 Steps)

```
Step 1:   Replace Unicode artifacts (non-breaking spaces, null bytes, soft hyphens)
Step 1b:  Resolve typographic ligatures (ﬁ→fi, ﬂ→fl, ﬀ→ff)
Step 1c:  Remove control characters (ASCII 0-31 except \n, \r, \t)
Step 2:   Normalize line endings (\r\n → \n)
Step 3:   Fix hyphenated line breaks ("com-\npany" → "company")
Step 4:   Remove page numbers ("Page 42", "- 42 -", standalone digits)
Step 5:   Remove company/year header patterns (regex-based)
Step 5b:  Auto-detect repeated headers (frequency counting, remove 8+ occurrences)
Step 6:   Normalize bullet points (●, ▪, ► → •)
Step 7:   Normalize whitespace (collapse spaces/tabs, collapse blank line runs)
Step 8:   Remove very short lines (1-2 char noise)
Step 8.5: Second blank-line collapse (cleanup after Step 8 side effects)
Step 9:   Strip trailing whitespace + final trim
```

---

## 💡 Interview Talking Points

> "In Phase 1, I built the complete ingestion pipeline for FinRAG — a financial RAG system. I processed 21 real annual reports from companies like NVIDIA, JPMorgan, and HDFC Bank (5,350 pages total). The text pipeline extracts text using PyMuPDF, applies a 10-step cleaning process that handles PDF artifacts like typographic ligatures, control characters, and auto-detects repeated headers using frequency analysis. It then chunks text using a sliding window with smart boundary detection — producing 24,948 searchable chunks.
>
> I also built a structured table extractor using PyMuPDF's find_tables(). I hit a major performance challenge — initial approaches took 20+ minutes. I solved it with a pre-check heuristic that counts drawn line segments before calling expensive table detection, skipping ~80% of pages. This reduced JPMorgan 2024 from hanging indefinitely to 57 seconds.
>
> I ran a 13-check quality audit across all files, catching edge cases like unresolved ligatures in TCS reports (100+ instances of 'ﬁ' instead of 'fi') and 1,197 hidden control characters in Reliance reports. The pipeline is modular, idempotent, and has two modes — fast text-only batch (35 seconds) and comprehensive extraction with tables."

---

## 📁 Current Project Structure

```
nlp_project/
├── .env                              # Environment config
├── requirements.txt                  # Dependencies
├── backend/
│   ├── main.py                       # Entry point
│   ├── core/
│   │   ├── config.py                 # Pydantic BaseSettings
│   │   └── logging.py               # Structured logging
│   ├── pipelines/
│   │   ├── pdf_extractor.py          # PDF → text
│   │   ├── text_cleaner.py           # Raw text → clean text (10 steps)
│   │   ├── chunker.py               # Clean text → chunks
│   │   ├── table_extractor.py        # PDF → structured tables
│   │   └── ingest.py                # Orchestrator (--tables flag)
│   ├── api/                          # (Phase 5)
│   ├── services/                     # (Phase 3+)
│   ├── engines/                      # (Phase 2+)
│   ├── workers/                      # (Phase 6)
│   ├── llm/                          # (Phase 3)
│   └── db/                           # (Phase 2)
├── data/                             # 21 raw PDFs
│   ├── india/annual/{hdfcbank,reliance,tcs}/
│   └── us/annual/{jpmorgan,nvidia,pfizer,walmart}/
└── processed/                        # Output from pipeline
    ├── ingestion_summary.json
    ├── india/annual/{company}/
    │   └── {company}_{year}_annual.txt + _chunks.json + _tables.json + _tables.md
    └── us/annual/{company}/
        └── {company}_{year}_annual.txt + _chunks.json + _tables.json + _tables.md
```

---

## 📂 Why This Directory Structure?

The `processed/` directory **mirrors** the `data/` directory layout:

```
data/india/annual/hdfcbank/hdfcbank_2024_annual.pdf
                    ↓ pipeline processes ↓
processed/india/annual/hdfcbank/hdfcbank_2024_annual.txt
processed/india/annual/hdfcbank/hdfcbank_2024_annual_chunks.json
processed/india/annual/hdfcbank/hdfcbank_2024_annual_tables.json
processed/india/annual/hdfcbank/hdfcbank_2024_annual_tables.md
```

**Why mirror?**
- **Traceability:** Given any output file, you can instantly find the source PDF by swapping `processed/` for `data/`
- **Scalability:** Adding a new company or region just means adding a folder — no config changes
- **Metadata from path:** The path itself encodes `region/report_type/company/` — we parse this instead of trying to extract metadata from PDF content (which is unreliable)
- **Idempotency:** Re-running the pipeline overwrites the same files in the same locations — no duplicates

---

## 📄 Why 4 Output Files Per PDF?

Each file serves a **different consumer** in the RAG system:

| File | Who Reads It | Why It Exists |
|------|-------------|---------------|
| `_annual.txt` | Humans + chunker | Cleaned text for reading and for the chunking step. Useful for manual inspection. |
| `_chunks.json` | Database (Phase 2) | Text chunks with metadata (company, year, region, chunk index). Gets loaded into PostgreSQL with vector embeddings. |
| `_tables.json` | Our code / database | Structured table data (headers + rows as arrays). Easy to parse programmatically, load into DB, or convert to other formats. |
| `_tables.md` | The LLM (Phase 3+) | Markdown-formatted tables ready to inject into LLM prompts. LLMs understand Markdown tables natively — they can read `\| Revenue \| $5B \|` and answer questions directly. Uses fewer tokens than JSON. |

**Key insight:** The `.md` table file is NOT for us to read — it's a **pre-formatted context document** designed for the LLM. When someone asks "What was NVIDIA's revenue in 2024?", the RAG system retrieves the relevant `_tables.md` content and injects it into the prompt alongside text chunks. The LLM reads the Markdown table and answers accurately.

**Why not just one format?** Different consumers need different things:
- Code needs structure (JSON arrays) → `.json`
- LLMs need readability (Markdown) → `.md`  
- Humans need plain text → `.txt`
- If we only had JSON, we'd waste tokens converting it for the LLM every time
- If we only had Markdown, we'd struggle to programmatically query columns/rows

---

## ➡️ What's Next: Phase 2 — Embeddings & Vector Search

We'll convert these 24,948 text chunks into mathematical vectors (embeddings) that a computer can search through. This is where the "AI" starts — turning text into numbers that encode meaning, so "revenue growth" and "sales increase" would be close together in vector space.

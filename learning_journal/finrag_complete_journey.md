# FinRAG: The Complete Engineering Journey (Phase 1 to Phase 9)

**Project:** FinRAG (Financial Retrieval-Augmented Generation)  
**Goal:** Build an end-to-end, production-ready AI chat system for massive financial documents (10-Ks, Annual Reports).

*This document is a complete compilation of the engineering decisions, challenges, and deep technical summaries from every phase of the project. It serves as an exhaustive interview preparation guide.*

## � Table of Contents
1. [Phase 1: Foundation & PDF Ingestion](#-phase-1-learning-journal--foundation--pdf-ingestion) (Extraction, Cleaning, Sliding Window Chunking)
2. [Phase 2: Embeddings & Vector Search](#-phase-2-learning-journal--embeddings--vector-search) (SentenceTransformers, Cosine Similarity, SQLite ORM)
3. [Phase 3: The RAG Pipeline](#-phase-3-learning-journal--rag-pipeline) (Gemini LLM Integration, Prompt Engineering, Grounding)
4. [Phase 5: Backend API Layer](#-phase-5-learning-journal--fastapi-deployment) (FastAPI, Uvicorn, REST endpoints)
5. [Phase 7: The Frontend UI](#-phase-7-learning-journal--react-frontend) (React, Vite, Tailwind Glassmorphism)
6. [Phase 9: Advanced Optimization & UX](#-phase-9-advanced-optimization-ux--polish) (Hybrid Search RRF, Caching, SSE Streaming, Conversational Memory)

---

# �📓 Phase 1 Learning Journal — Foundation & PDF Ingestion
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
# 📓 Phase 2 Learning Journal — Embeddings & Vector Search

**Date:** February 16–22, 2026
**Duration:** ~2 hours of coding
**Result:** ✅ 23,343 text chunks embedded and stored → Semantic search working

---

## 🗂️ Files Created (in order)

| # | File | Purpose |
|---|------|---------|
| 1 | `requirements.txt` (updated) | Added sentence-transformers, sqlalchemy, numpy |
| 2 | `backend/core/config.py` (updated) | Added embedding_model, embedding_dim, database_url |
| 3 | `.env` (updated) | Added EMBEDDING_MODEL, DATABASE_URL |
| 4 | `backend/engines/embedder.py` | Embedding engine with model loading + cosine similarity |
| 5 | `backend/db/database.py` | Database engine, sessions, init_db |
| 6 | `backend/db/models.py` | SQLAlchemy ORM models (Document, Chunk) |
| 7 | `backend/pipelines/store_embeddings.py` | Read chunks → embed → store in SQLite |
| 8 | `backend/engines/search.py` | Semantic search engine with filtering |

---

## 🧠 Key Concepts Learned

### 1. What Are Embeddings?
**What:** Text converted to a list of numbers (a vector) that encodes its **meaning**.
- "revenue growth" → `[0.12, -0.34, 0.56, ...]` (384 numbers)
- "sales increase" → `[0.11, -0.31, 0.54, ...]` (very close!)
- "the weather today" → `[0.89, 0.23, -0.67, ...]` (very different!)

**Why they matter:** Computers can compare numbers but not understand text. Embeddings make "revenue growth" and "sales increase" retrievable with the same query because their vectors point in a similar direction.

### 2. Sentence Transformers
**What:** Pre-trained deep learning models that convert sentences into embeddings.
**Model used:** `all-MiniLM-L6-v2`
- 384 dimensions (small = fast)
- 80MB download, fits anywhere
- Trained on 1 billion sentence pairs
- Top performance/speed ratio on MTEB benchmark
**How to use:**
```python
model = SentenceTransformer("all-MiniLM-L6-v2")
vec = model.encode("What was NVIDIA's revenue?")  # → (384,) numpy array
```

### 3. Cosine Similarity
**What:** Measures the angle between two vectors — are they pointing in the same direction?
```
cos(θ) = (A · B) / (||A|| × ||B||)
```
- `1.0` = identical direction (same meaning)
- `0.0` = perpendicular (unrelated)
- `-1.0` = opposite direction

**Key optimization:** If vectors are **normalized** (unit length = 1), then cosine similarity = dot product — just one matrix multiplication.
```python
# Why normalize_embeddings=True in encode():
embeddings = model.encode(texts, normalize_embeddings=True)
# Now: cosine_similarity = np.dot(A, B)  — super fast!
```

### 4. Batch Embedding
**What:** Processing multiple texts together instead of one at a time.
**Why it's faster:** CPUs are optimized for parallel math. 64 texts at once uses hardware efficiently.
```python
# SLOW: one at a time
for text in texts:
    vec = model.encode(text)

# FAST: batch of 64
vecs = model.encode(texts, batch_size=64)  # ~50x faster!
```

### 5. ORM (Object-Relational Mapping) with SQLAlchemy
**What:** Translates between Python objects and database rows automatically.

**Without ORM (raw SQL):**
```python
cursor.execute("INSERT INTO chunks (text, company) VALUES (?, ?)", (text, company))
```

**With ORM (SQLAlchemy):**
```python
chunk = Chunk(text=text, company=company)
session.add(chunk)
session.commit()
```

**Why ORM:** Type safety, IDE autocomplete, no SQL string typos, and — most importantly — **database-agnostic**: the same Python code runs on both SQLite and PostgreSQL.

### 6. SQLite vs PostgreSQL (via SQLAlchemy)
**Key insight:** SQLAlchemy abstracts the database so the ONLY difference is the connection string:
```python
# SQLite (development — zero setup)
DATABASE_URL = "sqlite:///finrag.db"

# PostgreSQL (production)
DATABASE_URL = "postgresql://user:pass@localhost:5432/finrag"
```
Everything else — models, queries, sessions — stays **identical**.

### 7. Storing Embeddings as Binary
**Why binary (not JSON)?**
| Format | Size per chunk | Load speed |
|--------|---------------|-----------|
| JSON array | ~3-4 KB | Slow (text parsing) |
| Binary blob | ~1.5 KB | Fast (direct memory copy) |

```python
# Store: numpy array → binary bytes
chunk.embedding = embedding.astype(np.float32).tobytes()

# Load: binary bytes → numpy array
vec = np.frombuffer(chunk.embedding, dtype=np.float32)
```

### 8. Normalization vs Denormalization in Databases
**Normalized:** `chunks` table has a `document_id` FK → join to get company/year.
**Denormalized:** `chunks` table also has `company` and `year` columns directly.

**Why we denormalize for search:** Every search query can filter by company/year. If these fields were only in the `documents` table, every query would require an expensive JOIN. By copying them to `chunks`, filters are instant (indexed column lookups).

**Trade-off:** A bit more storage (company name repeated 1,000+ times), but much faster search. This is a **standard pattern in search systems.**

### 9. Idempotent Data Loading
**What:** Running the pipeline twice doesn't create duplicates.
```python
# Check before inserting
existing = session.query(Document).filter_by(file_name=file_name).first()
if existing:
    logger.info("Already stored, skipping")
    return 0  # Skip
```
**Why:** If the pipeline fails halfway through, you can safely re-run it without corrupting the database.

### 10. Semantic Search End-to-End
**The full flow:**
```
User query: "What was NVIDIA's revenue in 2024?"
      │
      ▼ embed_text()
Query vector: [0.12, -0.34, 0.56, ...]
      │
      ▼ load all chunk embeddings from DB
23,343 vectors of shape (384,)
      │
      ▼ cosine_similarity() → np.dot()
Scores: [0.32, 0.71, 0.18, 0.65, ...]
      │
      ▼ np.argsort()[::-1][:top_k]
Top-5 chunk indices
      │
      ▼ return SearchResult objects
[{text: "NVIDIA reported revenue of $60.9B...", score: 0.71, company: "nvidia"}]
```

---

## ⚡ Challenges Faced & Solutions

### Challenge #1: Terminal output truncation
**What happened:** Search test results were too long for the terminal capture in our automated tool.
**Fix:** Ran targeted queries with short output format. Full results visible via direct Python import.

### Challenge #2: Embedding 24,948 chunks takes time on CPU
**What happened:** Embedding pipeline took ~20-25 minutes total (no GPU).
**Why acceptable:** This is a **one-time cost** — once embedded, search queries run in <100ms because we're just doing dot products.
**Lesson:** Expensive preprocessing is acceptable if it makes real-time queries fast. Cache/precompute where you can.

### Challenge #3: SQLite WAL mode
**What:** Added `PRAGMA journal_mode=WAL` for better concurrent read/write.
**Why:** WAL (Write-Ahead Logging) allows readers and writers to work simultaneously without blocking each other.

---

## 📊 Pipeline Results

| Metric | Value |
|--------|-------|
| Documents stored | 21 |
| Chunks embedded | 23,343 |
| Embedding model | all-MiniLM-L6-v2 |
| Vector dimensions | 384 |
| Database | SQLite (`finrag.db`) |
| Storage size | ~135MB (text + embeddings) |
| Search query time | <100ms |
| Top search score | ~0.68 (risk factors) |

---

## 🔬 Phase 2 Architecture

```
Phase 1 output          Phase 2 pipeline             Search
────────────────        ──────────────────────────    ─────────
_chunks.json files  →  load → embed → store     →   embed query
(24,948 chunks)        store_embeddings.py            search()
                            │                             │
                            ▼                             ▼
                        SQLite DB                    cosine_similarity
                        ├── documents (21 rows)      np.dot(q, D)
                        └── chunks (23,343 rows)
                            ├── text                 return top-K
                            ├── embedding (bytes)    SearchResult[]
                            └── company/year/region
```

---

## 💡 Interview Talking Points

> "In Phase 2, I built the embedding and vector search layer for FinRAG. I chose `sentence-transformers/all-MiniLM-L6-v2` — 384-dimensional embeddings, 80MB model, top MTEB benchmark performance for its size class. I store embeddings as binary blobs in SQLite (1.5KB per chunk vs 4KB JSON), and use numpy cosine similarity for search.
>
> For the database, I used SQLAlchemy ORM which abstracts away the database entirely — the same model code runs on SQLite for development and PostgreSQL for production. The only change is one connection string. I also denormalized company/year into the chunks table specifically for fast search filtering — a deliberate trade-off of storage space for query speed.
>
> The result: 23,343 chunks embedded and searchable. Search queries run in under 100ms against the full dataset. 'NVIDIA data center performance' correctly retrieves NVIDIA-specific revenue discussions, and 'risk factors' retrieves cross-company risk sections with 0.68 similarity scores."

---

## 📁 What Got Added to Project Structure

```
nlp_project/
├── finrag.db                             ← NEW: SQLite database (23,343 chunks)
├── backend/
│   ├── core/
│   │   └── config.py                    ← UPDATED: embedding_model, database_url
│   ├── engines/                          ← NEW DIRECTORY IN USE
│   │   ├── embedder.py                  ← NEW: model loading, embed, cosine_sim
│   │   └── search.py                    ← NEW: semantic search with filtering
│   ├── pipelines/
│   │   └── store_embeddings.py          ← NEW: Phase 1 chunks → SQLite
│   └── db/                              ← NEW DIRECTORY IN USE
│       ├── database.py                  ← NEW: engine, sessions, init_db
│       └── models.py                    ← NEW: Document + Chunk ORM models
```

---

## ➡️ What's Next: Phase 3 — RAG Pipeline

With semantic search working, we can now build the full RAG pipeline:
1. User asks a question
2. Search retrieves relevant chunks (Phase 2 ✅)
3. LLM reads chunks + answers the question with citations (Phase 3)

This is where the intelligence kicks in — transforming retrieved text into accurate, sourced answers.
# 📓 Phase 3 Learning Journal — RAG Pipeline

**Date:** February 22, 2026
**Duration:** ~1 hour
**Result:** ✅ Full RAG pipeline working — questions answered with citations in 6.4s

---

## 🗂️ Files Created

| # | File | Purpose |
|---|------|---------|
| 1 | `backend/llm/llm_client.py` | LLM abstraction (Gemini implementation) |
| 2 | `backend/llm/prompt_builder.py` | RAG prompt templates + citation formatting |
| 3 | `backend/services/rag_pipeline.py` | Orchestrator: search → prompt → LLM → answer |
| 4 | `backend/core/config.py` (updated) | Added LLM settings (model, temperature, API key) |

---

## 🧠 Key Concepts Learned

### 1. What Is RAG (Retrieval-Augmented Generation)?

**The Problem:**
- LLMs like Gemini/GPT have a knowledge cutoff date — they don't know YOUR documents
- If you ask "What was NVIDIA's 2024 revenue?", the LLM might hallucinate or say outdated info

**The Solution (RAG):**
```
User question
    │
    ▼ RETRIEVE: Search your database for relevant chunks
    │
    ▼ AUGMENT: Inject those chunks into the prompt as context
    │
    ▼ GENERATE: LLM reads the context and generates a grounded answer
```

**Key insight:** RAG doesn't make the LLM smarter — it gives the LLM the RIGHT INFORMATION to work with. The LLM is just a "reader" of your data.

### 2. The Strategy Pattern (Design Pattern)

**What:** Define an interface, then multiple implementations can be swapped.

```python
# Interface (what must be implemented)
class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

# Implementation 1: Gemini
class GeminiClient(BaseLLMClient):
    def generate(self, prompt): ...  # calls Gemini API

# Implementation 2 (future): OpenAI
class OpenAIClient(BaseLLMClient):
    def generate(self, prompt): ...  # calls OpenAI API
```

**Why it matters:** The entire RAG pipeline just calls `client.generate()`. Switching from Gemini to OpenAI = changing ONE config variable. No code changes.

**Interview answer:** "I used the Strategy pattern for LLM integration — a base class defines the interface, and each provider implements it. Switching from Gemini to OpenAI is a one-line config change."

### 3. Prompt Engineering for RAG

**Bad prompt:**
```
Here's some text. What was the revenue?
```

**Good prompt (what we built):**
```
SYSTEM: You are FinRAG, a financial analyst. Answer ONLY from
provided context. Use [Source N] citations. Say "I don't have
sufficient information" when data is missing.

CONTEXT:
[Source 1] NVIDIA, 2024 Annual Report (Relevance: 0.70)
Revenue for fiscal year 2024 reached $60.9 billion...

[Source 2] NVIDIA, 2024 Annual Report (Relevance: 0.69)
Data Center revenue was $47.5 billion...

QUESTION: What was NVIDIA's revenue in 2024?
Please cite your sources using [Source N] notation.
```

**Key design decisions:**
1. **System prompt** = the LLM's "job description" (financial analyst, cite sources)
2. **Numbered sources** = enables `[Source 1]` citation format
3. **Include relevance score** = helps LLM prioritize higher-relevance sources
4. **"Say I don't know"** = prevents hallucination when context is insufficient

### 4. System Prompt vs User Prompt

**System prompt:** WHO the LLM is and HOW it should behave
- "You are a financial analyst"  
- "Only use provided context"
- "Cite sources with [Source N]"

**User prompt:** WHAT to answer
- The context (retrieved chunks)
- The question

**Why separate?** Different LLM APIs handle them differently:
- Gemini: Prepended together
- OpenAI: Separate `role: "system"` message
- Some local models: Special `<|system|>` tokens

Our `build_rag_prompt()` returns both separately → provider-agnostic.

### 5. Temperature Setting

**What:** Controls randomness in LLM output.

| Temperature | Behavior | Use Case |
|-------------|----------|----------|
| `0.0` | Deterministic, same answer every time | Factual Q&A, code |
| `0.1` | Almost deterministic, tiny variation | **What we use** |
| `0.7` | Creative, varied answers | Creative writing |
| `1.0` | Very random | Brainstorming |

**Why 0.1 for financial RAG:** We want consistent, factual answers. Creativity = hallucination risk when answering "What was the revenue?"

### 6. The Lazy Singleton Pattern (Repeated)

We used this pattern AGAIN for the LLM client:
```python
_client = None

def get_llm_client():
    global _client
    if _client is None:
        _client = GeminiClient()  # Created once on first use
    return _client
```

**Where we've used it so far:**
1. `config.py` → Settings object
2. `embedder.py` → Embedding model
3. `llm_client.py` → LLM client

**Why keep repeating it:** Expensive resources (models, API clients) should be loaded ONCE and reused. This is the standard pattern.

### 7. Retry with Exponential Backoff

**What:** When an API rate-limits you (HTTP 429), wait and retry.

```python
for attempt in range(3):
    try:
        response = api_call()
        return response
    except RateLimitError:
        wait = 5 * (attempt + 1)  # 5s, 10s, 15s
        time.sleep(wait)
```

**Why exponential:** Each retry waits LONGER, giving the rate limit more time to reset. This is a standard pattern for any API integration.

### 8. Service Layer Architecture

```
rag_pipeline.py (SERVICE layer — orchestration)
    ├── search.py (retrieval — Phase 2)
    ├── prompt_builder.py (prompt assembly)
    └── llm_client.py (generation)
```

**Why a separate service layer:** Each component is testable and replaceable independently:
- Swap search algorithm? Only touch `search.py`
- Change LLM? Only touch `llm_client.py`
- Modify prompt? Only touch `prompt_builder.py`
- The orchestrator (`rag_pipeline.py`) just connects them

### 9. Structured Response Objects

```python
@dataclass
class RAGResponse:
    answer: str           # The LLM's answer
    query: str            # Original question
    sources: list[dict]   # Source citations
    retrieval_time: float # Search time
    generation_time: float # LLM time
    total_time: float     # End-to-end time
```

**Why not just return a string?** Because the API/frontend needs:
- The answer (display to user)
- Sources (show citation cards)
- Timing (performance monitoring)

Structured responses make the API layer (Phase 5) trivial to build.

---

## ⚡ Challenges Faced & Solutions

### Challenge #1: Gemini Rate Limiting (429)
**What happened:** Rapid-fire testing hit the free tier per-minute limit.
**Fix:** Added retry logic with exponential backoff (5s, 10s, 15s delays).
**Lesson:** Always build retry logic for external APIs — they WILL fail.

### Challenge #2: Model Name Selection
**What happened:** `gemini-2.0-flash` was hitting rate limits consistently.
**Fix:** Switched to `gemini-2.5-flash` (newer, higher free-tier limits).
**Lesson:** API free tiers change — always have a fallback model.

### Challenge #3: Deprecated SDK Warning
**What happened:** `google.generativeai` package shows FutureWarning about switching to `google.genai`.
**Status:** Not urgent — current package works. Migration planned for later.

---

## 📊 Performance Results

| Metric | Value |
|--------|-------|
| Total query time | **6.37 seconds** |
| Retrieval time | 4.09s (includes first model load) |
| LLM generation time | 2.27s |
| Sources retrieved | 5 |
| Top relevance score | 0.700 |
| Answer quality | ✅ Correct, cited, segment breakdown |

**Note:** First query is slow (4s) because the embedding model loads. Subsequent queries are ~1-2s retrieval.

---

## 🎯 Example RAG Output

```
❓ What was NVIDIA revenue in 2024?

🤖 Answer:
NVIDIA's total revenue for fiscal year 2024 was $60.9 billion [Source 1].
This represents a significant increase of 126% compared to the previous
year [Source 1].

The company's platforms address four main markets:
- Data Center: $47.5 billion
- Gaming: $10.4 billion  
- Professional Visualization: $1.6 billion
- Automotive: $1.1 billion [Source 3]

📚 Sources:
[1] NVIDIA 2024 (relevance: 0.700)
[2] NVIDIA 2024 (relevance: 0.695)
[3] NVIDIA 2024 (relevance: 0.683)
```

---

## 💡 Interview Talking Points

> "For Phase 3, I built the full RAG pipeline connecting semantic search to Google Gemini. The architecture uses the Strategy pattern for LLM integration — there's an abstract base class, and each provider just implements `generate()`. Switching from Gemini to OpenAI is a one-line config change.
>
> The prompt engineering was critical. I built a financial domain system prompt that instructs the LLM to only use provided context, cite sources with [Source N] notation, and admit when data is insufficient. Temperature is set to 0.1 for deterministic, factual answers.
>
> End-to-end, a query takes ~6 seconds: 2s for search, 2s for Gemini. The answer correctly returned NVIDIA's $60.9B revenue with a segment breakdown, all properly cited from the actual annual report."

---

## 📁 Updated Project Structure

```
backend/
├── llm/                          ← NEW DIRECTORY IN USE
│   ├── __init__.py
│   ├── llm_client.py            ← NEW: Gemini client + Strategy pattern
│   └── prompt_builder.py        ← NEW: RAG prompt templates
├── services/                     ← NEW DIRECTORY IN USE
│   ├── __init__.py
│   └── rag_pipeline.py          ← NEW: RAG orchestrator
├── engines/
│   ├── embedder.py              (Phase 2)
│   └── search.py                (Phase 2)
└── core/
    └── config.py                ← UPDATED: LLM settings
```

---

## ➡️ What's Next: Phase 4 or Phase 5

The core RAG system (Phases 1-3) is **complete**. Two paths forward:
- **Phase 4 (Analytics):** Add sentiment analysis, risk classification, theme extraction
- **Phase 5 (FastAPI):** Add REST API endpoints → enables the upload/search UI
# 📓 Phase 5 Learning Journal — FastAPI API Layer

**Date:** February 22, 2026
**Duration:** ~30 minutes
**Result:** ✅ REST API with 6 endpoints — upload, search, ask, documents, delete, health

---

## 🗂️ Files Created

| # | File | Purpose |
|---|------|---------|
| 1 | `backend/api/schemas.py` | Pydantic request/response models |
| 2 | `backend/api/routers/documents.py` | Upload, list, delete endpoints |
| 3 | `backend/api/routers/search.py` | Search and RAG Q&A endpoints |
| 4 | `backend/main.py` (rewritten) | FastAPI app with CORS and routers |

---

## 🧠 Key Concepts Learned

### 1. What Is FastAPI?

A modern Python web framework for building APIs. Key advantages:
- **Automatic validation** via Pydantic
- **Auto-generated docs** (Swagger UI at `/docs`)
- **Async support** (handles concurrent requests)
- **Type hints** drive everything

```python
@app.post("/api/ask")
async def ask(request: AskRequest):  # ← Pydantic model
    # FastAPI auto-validates the request body
    # If "question" is missing → 422 error with clear message
    return {"answer": "..."}
```

### 2. Pydantic Schemas (API Contracts)

**What:** Python classes that define the exact shape of request/response data.

```python
class AskRequest(BaseModel):
    question: str = Field(..., min_length=3)  # Required, min 3 chars
    company: str | None = None                # Optional
    top_k: int = Field(5, ge=1, le=20)        # Default 5, range 1-20
```

**Why this matters:**
- Invalid request? → Automatic 422 error with details
- Missing field? → Clear "field required" message
- Wrong type? → "expected string, got integer" message
- No manual validation code needed!

### 3. Routers (Code Organization)

**Problem:** Putting all 6 endpoints in `main.py` = messy 500-line file.

**Solution:** Group related endpoints into routers:
```
main.py
├── app.include_router(documents.router)  → /api/upload, /api/documents
└── app.include_router(search.router)     → /api/search, /api/ask
```

**Analogy:** Routers are like chapters in a book. Each chapter covers a topic, but they're all part of the same book (app).

### 4. CORS Middleware (Cross-Origin Resource Sharing)

**The Problem:**
```
React app (localhost:3000)  →  API (localhost:8000)
Browser says: "BLOCKED! Different origin!"
```

**Why browsers do this:** Security — prevents random websites from calling your API.

**The Fix:** Explicitly tell the API which origins are allowed:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Interview answer:** "CORS is a browser security policy that blocks cross-origin requests. We whitelist our frontend's origin in the API middleware to allow communication."

### 5. HTTP Status Codes

| Code | Meaning | When We Use It |
|------|---------|---------------|
| `200` | OK | Successful GET, POST |
| `201` | Created | After successful upload |
| `404` | Not Found | Document ID doesn't exist |
| `409` | Conflict | Document already uploaded |
| `422` | Unprocessable | Invalid request data |
| `500` | Server Error | Database or pipeline failure |

### 6. File Upload in FastAPI

```python
@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    # file.filename → "nvidia_2024_annual.pdf"
    # file.file → the actual file bytes (file-like object)
    
    # Save to temp, process, then clean up
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        # Process the PDF...
```

**Why `python-multipart` is needed:** FastAPI uses it under the hood to parse `multipart/form-data` requests (the standard format for file uploads).

### 7. POST vs GET for Search

**Traditional:** `GET /search?q=query&company=nvidia`
**Our approach:** `POST /search` with JSON body

**Why POST?**
1. Complex filters (company, year, region) get messy in query strings
2. Long queries can exceed URL length limits
3. JSON body is more extensible
4. Modern search APIs (Elasticsearch, OpenAI) all use POST

### 8. Swagger/OpenAPI Auto-Documentation

FastAPI automatically generates interactive API docs at `/docs`:
- Every endpoint listed with descriptions
- Try-it-out feature — test endpoints directly
- Request/response schemas shown
- All from your Python type hints — ZERO manual documentation

**Interview answer:** "FastAPI auto-generates OpenAPI documentation from Pydantic schemas and type hints. Every endpoint is testable from the browser at `/docs`."

---

## ⚡ Challenges & Solutions

### Challenge: PowerShell `curl` is `Invoke-WebRequest`
**Issue:** PowerShell aliases `curl` to `Invoke-WebRequest`, not actual curl.
**Fix:** Use `Invoke-RestMethod` for clean JSON responses.

---

## 📊 Test Results

| Endpoint | Status | Response |
|----------|--------|----------|
| `GET /api/health` | ✅ 200 | 21 documents, 23,343 chunks |
| `GET /api/documents` | ✅ 200 | List of all documents with IDs |
| `POST /api/search` | ✅ 200 | NVIDIA revenue chunks returned |
| Swagger UI | ✅ | Available at http://localhost:8000/docs |

---

## 📁 Updated Project Structure

```
backend/
├── main.py                          ← REWRITTEN: FastAPI app
├── api/
│   ├── schemas.py                   ← NEW: Pydantic models
│   └── routers/
│       ├── documents.py             ← NEW: Upload, list, delete
│       └── search.py                ← NEW: Search, ask
├── services/
│   └── rag_pipeline.py              (Phase 3)
├── engines/
│   ├── search.py                    (Phase 2)
│   └── embedder.py                  (Phase 2)
└── llm/
    ├── llm_client.py                (Phase 3)
    └── prompt_builder.py            (Phase 3)
```

---

## 💡 Interview Talking Points

> "In Phase 5, I built the REST API using FastAPI. The API has 6 endpoints: PDF upload with full pipeline processing, semantic search, RAG Q&A with citations, document listing, and deletion. I used Pydantic schemas for automatic request validation and OpenAPI doc generation.
>
> The upload endpoint is the most complex — it receives a PDF via multipart upload, then runs the entire Phase 1-2 pipeline inline: extract → clean → chunk → embed → store. This makes the system fully self-contained.
>
> I added CORS middleware to allow the React frontend to communicate with the API, and designed the API to return structured JSON responses with timing information for performance monitoring."

---

## ➡️ What's Next: Phase 7 — Frontend Dashboard
With the API ready, we can build a React frontend for:
- Document upload with drag-and-drop
- Search bar with company/year filters
- AI Q&A with source citation display
# 📓 Phase 7 Learning Journal — React Frontend

**Date:** February 22, 2026
**Duration:** ~30 minutes
**Result:** ✅ Full-stack web app — React dashboard connects to FastAPI backend

---

## 🗂️ Files Created

| # | File | Purpose |
|---|------|---------|
| 1 | `frontend/src/api/client.js` | Fetch wrappers for all API endpoints |
| 2 | `frontend/src/App.jsx` | Router + layout with gradient background |
| 3 | `frontend/src/components/Navbar.jsx` | Glassmorphism navigation bar |
| 4 | `frontend/src/pages/Dashboard.jsx` | Stats cards + document table |
| 5 | `frontend/src/pages/AskSearch.jsx` | RAG Q&A + semantic search |
| 6 | `frontend/src/pages/Upload.jsx` | Drag-and-drop PDF upload |
| 7 | `frontend/src/index.css` | Tailwind v3 + custom component classes |
| 8 | `frontend/tailwind.config.js` | Custom dark theme + colors |
| 9 | `frontend/vite.config.js` | Vite 7 + PostCSS fix |

---

## 🧠 Key Concepts Learned

### 1. Vite — Modern Build Tool

**What:** Vite replaces webpack. It's MUCH faster because it uses native ES modules during dev — no bundling needed until production.

**Why Vite over Create React App?**
- CRA is deprecated/unmaintained
- Vite starts in ~300ms vs CRA's ~10-30 seconds
- Hot module replacement (HMR) is instant

### 2. React Router (Client-Side Routing)

```jsx
<BrowserRouter>
  <Routes>
    <Route path="/" element={<Dashboard />} />
    <Route path="/ask" element={<AskSearch />} />
    <Route path="/upload" element={<Upload />} />
  </Routes>
</BrowserRouter>
```

**Key insight:** No page reload when navigating — React swaps components in-place. The URL changes but it's all happening in the browser.

### 3. Tailwind CSS — Utility-First Approach

**Traditional CSS:**
```css
.button { background: blue; padding: 12px; border-radius: 8px; }
```

**Tailwind:**
```jsx
<button className="bg-blue-500 px-4 py-3 rounded-lg">
```

**Why it matters:** No switching between CSS and JSX files. Styles are co-located with the component.

### 4. Glassmorphism Design Pattern

```css
.glass-card {
  @apply bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl;
}
```

**What:** Semi-transparent, blurred background — gives a "frosted glass" effect. Modern, premium look.

### 5. API Client Pattern (Separation of Concerns)

```
Component → calls client.js → fetch() → Backend API
```

**Why a separate client?** If the API URL changes, we update ONE file. Components don't know about `fetch()`, URLs, or headers.

### 6. CORS in Practice

**Frontend (port 5173) → Backend (port 8000):**
- Without CORS config → Browser blocks the request
- With CORS middleware in FastAPI → Works seamlessly

### 7. Vite 7 + Tailwind v3 Gotcha

**Problem:** Vite 7 uses Lightning CSS by default, which doesn't understand `@tailwind` directives.

**Fix:** Add `css: { transformer: 'postcss' }` to `vite.config.js`.

**Lesson:** Always check compatibility between tool versions.

---

## 📊 Architecture Overview

```
Browser (localhost:5173)         Server (localhost:8000)
┌─────────────────────┐         ┌──────────────────────┐
│  React + Tailwind   │───API──→│  FastAPI              │
│  ├── Dashboard      │         │  ├── /api/health      │
│  ├── Ask & Search   │         │  ├── /api/ask         │
│  └── Upload         │         │  ├── /api/search      │
│                     │         │  ├── /api/documents   │
│  client.js → fetch()│         │  └── /api/upload      │
└─────────────────────┘         └──────────────────────┘
```

---

## 💡 Interview Talking Points

> "For the frontend, I built a React dashboard with Vite and Tailwind CSS. The UI has three main views: a Dashboard showing document stats and a management table, an Ask & Search page for RAG Q&A with company/year filters, and a PDF Upload page with drag-and-drop.
>
> The design uses glassmorphism — semi-transparent cards with backdrop blur on a dark gradient background. I built a centralized API client module so all backend communication goes through one file.
>
> One interesting challenge was Vite 7's default Lightning CSS engine not supporting Tailwind's `@tailwind` directives — I had to explicitly configure PostCSS as the CSS transformer."

---

## ➡️ How to Run

```bash
# Terminal 1: Backend
venv\Scripts\uvicorn backend.main:app --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

Then open **http://localhost:5173** in your browser.
# 🚀 Phase 9: Advanced Optimization, UX & Polish
**Goal:** Take our MVP RAG system from "functional" to a "production-ready" chat experience. We added Hybrid Search for better retrieval, In-Memory Caching for speed/cost, Server-Sent Events (SSE) for real-time text streaming, conversational memory for follow-up questions, and polished CSS animations.

---

## 🏗️ 1. Hybrid Search (Vector + BM25)
**The Problem:** Vector search (Cosine Similarity) is great for "semantic" meaning, but it struggles with exact keyword matching (like catching an explicit mention of "10-K" or specific part numbers).

**The Solution:** Hybrid search combines two mechanisms and re-ranks the results:
1.  **Dense Retrieval (Vector Search):** We kept our `all-MiniLM-L6-v2` embeddings. Finds paragraphs *conceptually* related to the query.
2.  **Sparse Retrieval (BM25):** We added `rank_bm25` (Okapi BM25). This is a token-based algorithm that excels at exact keyword matching.
3.  **Reciprocal Rank Fusion (RRF):** This algorithm combines the results. It looks at the *rank* (position) of a document in both lists and assigns a combined score: `RRF_Score = 1 / (k + Vector_Rank) + 1 / (k + BM25_Rank)`.

**Why it matters:** It gives us the best of both worlds. If a user asks *"What was the exact EPS for TCS?"*, BM25 catches "EPS", while Vector Search catches the financial context.

---

## 🚦 2. Smart Company Detection & Diversified Retrieval
**The Problem:** 
- If a user asked *"Compare revenue targets"*, vector search might pull 5 paragraphs all from *one* company (e.g. NVIDIA) if that doc was just highly matched, completely missing the "comparison" aspect.
- Conversely, if a user asked *"revenue of tcs"*, the system might distribute retrieved chunks across 8 different companies if no filter was explicitly set.

**The Solution:**
1.  **Auto-detection:** We built logic to scan the user's query lowercase string against known companies in the database (`f" {company} " in query_lower`). If detected, we automatically set `company="tcs"`.
2.  **Diversified Round-Robin:** If NO company filter is set (a true cross-company query), we temporarily boost `top_k` up to 10+. Then, we group the raw retrieved chunks by company and select them "Round Robin" (one from A, one from B, one from C...) until we hit our target. 

**Why it matters:** This ensures cross-company questions actually get data from multiple companies, while explicit questions don't get diluted by irrelevant companies.

---

## ⚡ 3. In-Memory Answer Caching
**The Problem:** Calling the LLM API (Gemini) takes 3-8 seconds and costs quota/money. If 5 users ask *"What is the dashboard status?"*, we shouldn't ask the LLM 5 times.

**The Solution:** We implemented an in-memory dictionary cache in `backend/engines/cache.py`.
- **The Key:** A SHA-256 hash of the normalized query + filters (e.g., `hash("what is revenue?|tcs|None|None")`).
- **The Cache Entry:** Stores the generated answer, the source chunks, and timestamp.
- **Eviction / TTL:** The cache holds a max of 500 entries (LRU-style eviction) and entries expire after 1 hour (TTL).
- **Invalidation:** *Crucially*, when a user adds or deletes a PDF (`/api/documents`), we `cache.invalidate()` to wipe the cache. Stale data is a huge risk in financial tasks.

**Why it matters:** 0.001s response times for repeated queries, 0 API cost.

---

## 📡 4. Streaming Responses (SSE)
**The Problem:** Waiting 8 seconds staring at a spinner is terrible UX. Users think the app is broken.

**The Solution:** Server-Sent Events (SSE). 
- **Backend (`yield`):** We switched from `generate_content` to `generate_content_stream()`. The endpoint now uses FastAPIs `StreamingResponse`, yielding partial text chunks (tokens) as they arrive.
- **Frontend (`TextDecoder`):** We ditched `await response.json()`. Instead, we use `response.body.getReader()`, decode the byte stream, and apply incoming tokens directly to React state (`setStreamingText(prev => prev + token)`).

**Why it matters:** The perceived latency drops to < 1 second. The user starts reading *immediately*, matching the UX of ChatGPT.

---

## 💬 5. Chat History (Conversational Memory)
**The Problem:** RAG models have "goldfish memory." Each API call is totally isolated. You can't ask *"What about their risks?"* after asking about revenue, because the LLM doesn't know who "their" is.

**The Solution:**
1.  **React State:** Frontend maintains a `messages` array holding the history of the current conversation session.
2.  **API Payload:** We changed `AskRequest` to `ChatRequest`, accepting a `history: list[ChatMessage]` field.
3.  **Prompt Injection:** In the backend `ask_stream()` endpoint, we grab the last 6 messages (3 conversational turns), format them as a transcript (`User: ... \n Assistant: ...`), and inject them *before* the new question in the context window.

**Why it matters:** This transforms a simple "search bar" into a natural dialogue agent.

---

## 🎨 6. UI Polish (CSS & UX)
**The Problem:** The app looked basic. Text snapped into existence, and loading states were jarring.

**The Solution:**
- **Markdown Rendering:** Installed `react-markdown` so the LLM output renders nicely with bolding, lists, code blocks, and tables using specific CSS prose classes.
- **Skeleton Shimmers:** Replaced the loading spinner with CSS `background-position` animations that look like shimmering "placeholder" cards (Skeleton loaders) to match the layout of the incoming data.
- **CSS Keyframes:** Added `@keyframes fadeInUp` to stagger the entrance of cards, giving the app a fluid, modern feel.

**Why it matters:** The app now feels premium, responsive, and trustworthy.

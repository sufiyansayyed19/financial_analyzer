# 📓 Phase 1 Learning Journal — Foundation & PDF Ingestion

**Date:** February 15, 2026  
**Duration:** ~1 hour  
**Result:** ✅ All 21 PDFs successfully processed into 24,948 searchable chunks

---

## 🗂️ Files Created (in order)

| # | File | Purpose |
|---|------|---------|
| 1 | `requirements.txt` | Phase 1 dependencies: PyMuPDF, FastAPI, Pydantic, Rich |
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
| 16 | `backend/pipelines/text_cleaner.py` | 9-step text cleaning pipeline |
| 17 | `backend/pipelines/chunker.py` | Sliding window chunking with smart boundaries |
| 18 | `backend/pipelines/ingest.py` | End-to-end orchestration pipeline |

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
**Why it matters:** Much faster than alternatives like pdfplumber. Handles most digital PDFs well. Limitation: can't read scanned images (needs OCR).

### 6. Regex for text cleaning
**What:** Regular expressions — pattern matching language for text.  
**Key patterns used:**
- `r"(\w)-\s*\n\s*(\w)"` → fix hyphenated line breaks
- `r"^\s*\d{1,4}\s*$"` → remove standalone page numbers
- `r"\n{3,}"` → collapse excessive blank lines

### 7. Sliding Window Chunking
**What:** Split text using a window that moves `step = chunk_size - overlap` characters each time.  
**Why overlap:** Prevents losing context at chunk boundaries. A sentence split across two chunks will be complete in at least one.  
**Smart boundaries:** Instead of cutting at exact character count, we find the nearest paragraph or sentence break.

### 8. Pipeline Orchestration Pattern
**What:** Each component (extract, clean, chunk) is independent. A separate orchestrator (`ingest.py`) connects them.  
**Why it matters:** You can reuse any component alone. You can swap the extractor without touching the cleaner. This is the "separation of concerns" principle.

---

## ⚡ Challenges Faced & Solutions

### Challenge #1: Rich markup crashes in PowerShell piping
**What happened:** Log messages with `[bold green]` markup caused errors when output was piped (`|`).  
**Root cause:** Rich interprets `[bold]` as formatting commands, but piped output doesn't support terminal formatting.  
**Fix:** Set `markup=False` in `RichHandler` configuration.  
**Lesson:** Terminal-focused libraries behave differently in interactive vs piped mode. Always test both.

### Challenge #2: Financial PDFs have messy extracted text
**What happened:** Raw text from PyMuPDF contained:
- Repeated headers/footers on every page
- Page numbers as standalone lines
- Non-breaking spaces (`\xa0`) from PDF formatting
- Hyphenated word breaks across lines
- Garbled table columns

**Fix:** Built a 9-step sequential cleaner that handles each issue. Order matters — Unicode normalization comes before regex matching.  
**Lesson:** Text cleaning is 80% of real NLP work. Raw data is NEVER clean.

### Challenge #3: Deciding chunk size
**What happened:** Too small = loses context, too large = includes irrelevant info.  
**Decision:** 1000 chars with 200 overlap.  
**Result:** Average chunk ~932 chars — captures a complete paragraph or idea.  
**Lesson:** There's no universally "right" chunk size. It depends on your content and retrieval needs. We can tune later.

### Challenge #4: Avoiding mid-sentence cuts in chunks
**What happened:** Fixed-size chunks would split sentences: "revenue of" | "$60.9 billion".  
**Fix:** Smart boundary detection — look for `\n\n` (paragraph) > `. ` (sentence) > `\n` (line) in the last 20% of each chunk.  
**Lesson:** Small details like this significantly impact RAG quality later.

---

## 📊 Pipeline Results

**21 PDFs → 24,948 chunks in 35.7 seconds**

| Company | Region | Reports | Total Pages | Total Chunks |
|---------|--------|---------|-------------|--------------|
| HDFC Bank | India | 3 (2022-2024) | 1,458 | 5,358 |
| Reliance | India | 3 (2023-2025) | 573 | 4,262 |
| TCS | India | 3 (2023-2025) | 1,022 | 3,902 |
| JPMorgan | US | 3 (2022-2024) | 1,064 | 5,039 |
| NVIDIA | US | 3 (2023-2025) | 537 | 2,377 |
| Pfizer | US | 3 (2022-2024) | 402 | 2,567 |
| Walmart | US | 3 (2023-2025) | 294 | 1,443 |

---

## 🏗️ Architecture Decisions Made

1. **Pydantic BaseSettings** over plain dicts → type safety, `.env` support
2. **PyMuPDF** over pdfplumber → speed (can add pdfplumber for tables later)
3. **Dataclasses** over raw dicts → structured, type-safe data passing
4. **Metadata from file paths** over PDF content parsing → more reliable
5. **JSON + TXT** dual output → human-readable + machine-readable
6. **Idempotent pipeline** → safe to re-run without duplicates

---

## 💡 Interview Talking Points

> "In Phase 1, I built the ingestion pipeline for FinRAG. I processed 21 real financial annual reports from companies like NVIDIA and JPMorgan. The pipeline extracts text using PyMuPDF, applies a 9-step cleaning process to handle financial PDF artifacts like repeated headers and garbled tables, then chunks the text using a sliding window with smart boundary detection. The system produced 24,948 searchable chunks with metadata. I used Pydantic BaseSettings for configuration, structured logging with Rich, and designed the pipeline to be idempotent and modular."

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
│   │   ├── text_cleaner.py           # Raw text → clean text
│   │   ├── chunker.py               # Clean text → chunks
│   │   └── ingest.py                # Orchestrator
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
    ├── india/annual/{hdfcbank,reliance,tcs}/
    │   └── {company}_{year}_annual.txt + _chunks.json
    └── us/annual/{jpmorgan,nvidia,pfizer,walmart}/
        └── {company}_{year}_annual.txt + _chunks.json
```

---

## ➡️ What's Next: Phase 2 — Embeddings & Vector Search

We'll convert these 24,948 text chunks into mathematical vectors (embeddings) that a computer can search through. This is where the "AI" starts.

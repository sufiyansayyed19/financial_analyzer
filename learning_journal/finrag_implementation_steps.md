# FinRAG: Step-by-Step Implementation Summary

A clean, ordered walkthrough of every file created and every feature implemented — from empty folder to working app.

---

## Step 1: Project Setup
1. Created the folder structure: `backend/core/`, `backend/pipelines/`, `backend/engines/`, `backend/db/`, `backend/llm/`, `backend/api/`, `backend/services/`.
2. Added `__init__.py` to every folder to make them Python packages.
3. Created `requirements.txt` with all dependencies (PyMuPDF, FastAPI, SQLAlchemy, SentenceTransformers, etc.).
4. Created `.env` file for environment variables (API keys, model names, DB path).
5. Created `backend/core/config.py` — Pydantic `BaseSettings` class that reads from `.env` automatically.
6. Created `backend/core/logging.py` — colored terminal logging using the `rich` library.

---

## Step 2: PDF Text Extraction
7. Created `backend/pipelines/pdf_extractor.py` — uses PyMuPDF (`fitz`) to open a PDF and extract raw text from every page, skipping blank pages.
8. Collected 21 real financial PDFs (annual reports from NVIDIA, JPMorgan, TCS, HDFC Bank, Reliance, Pfizer, Walmart).

---

## Step 3: Text Cleaning
9. Created `backend/pipelines/text_cleaner.py` — a 10-step sequential cleaning pipeline:
   - Step 1: Replace non-breaking spaces, null bytes, soft hyphens.
   - Step 1b: Resolve typographic ligatures (`ﬁ` → `fi`, `ﬂ` → `fl`).
   - Step 1c: Remove invisible control characters.
   - Step 2: Normalize line endings (`\r\n` → `\n`).
   - Step 3: Fix broken hyphenated words (`com-\npany` → `company`).
   - Step 4: Remove standalone page numbers.
   - Step 5: Remove company/year header patterns using regex.
   - Step 5b: Auto-detect and remove repeated headers using frequency counting.
   - Step 6: Normalize bullet point characters to `•`.
   - Steps 7-9: Collapse blank lines, remove short noise lines, strip trailing whitespace.

---

## Step 4: Text Chunking
10. Created `backend/pipelines/chunker.py` — sliding window chunking.
    - Window size: 1000 characters.
    - Overlap: 200 characters.
    - Smart boundary detection: tries to break at `\n\n` (paragraph) > `. ` (sentence) > `\n` (line) in the last 20% of each chunk.

---

## Step 5: Table Extraction
11. Created `backend/pipelines/table_extractor.py` — extracts structured tables from PDFs using PyMuPDF's `find_tables()`.
    - Added a pre-check heuristic: count drawn line segments before calling `find_tables()`. Pages with fewer than 4 lines are skipped instantly.
    - Outputs tables as both `.json` (structured data) and `.md` (markdown for LLM prompts).

---

## Step 6: Ingestion Orchestrator
12. Created `backend/pipelines/ingest.py` — connects all pipeline steps together.
    - Reads PDFs from `data/` folder.
    - Runs extract → clean → chunk → (optionally) table extract.
    - Saves output to `processed/` folder mirroring the `data/` directory structure.
    - Supports `--tables` CLI flag to enable/disable table extraction.
    - Idempotent: skips already-processed files.

**Result:** 21 PDFs → 24,948 text chunks in ~35 seconds.

---

## Step 7: Database Setup
13. Created `backend/db/models.py` — SQLAlchemy ORM models:
    - `Document` table: id, file_name, company, year, region, report_type, created_at.
    - `Chunk` table: id, document_id (FK), chunk_index, text, embedding (BLOB), company, year, region.
    - Denormalized `company`, `year`, `region` onto Chunk table for fast search filtering.

14. Created `backend/db/database.py` — database engine setup:
    - SQLite with WAL mode for concurrent reads/writes.
    - Session factory using `sessionmaker`.
    - `init_db()` function to create all tables on startup.

---

## Step 8: Embedding Engine
15. Created `backend/engines/embedder.py` — wraps SentenceTransformers:
    - Loads `all-MiniLM-L6-v2` model (384 dimensions, 80MB).
    - `embed_text()`: converts a single string to a normalized vector.
    - `embed_batch()`: converts multiple strings to vectors in batches of 64.
    - Uses lazy singleton pattern — model loaded once on first use.

---

## Step 9: Store Embeddings in Database
16. Created `backend/pipelines/store_embeddings.py`:
    - Reads `_chunks.json` files from `processed/` folder.
    - Creates a `Document` row for each PDF.
    - Embeds all chunks in batches using the embedder.
    - Stores each embedding as binary bytes (`.tobytes()`) in the Chunk table.
    - Idempotent: skips files already in the database.

**Result:** 23,343 chunks embedded and stored in `finrag.db` (~135MB).

---

## Step 10: Semantic Search Engine
17. Created `backend/engines/search.py`:
    - `semantic_search()`: loads all chunk embeddings from DB, computes cosine similarity (dot product on normalized vectors), returns top-K results.
    - Supports filtering by company, year, region.
    - Returns `SearchResult` objects with text, score, metadata, and chunk ID.

---

## Step 11: LLM Client
18. Created `backend/llm/llm_client.py`:
    - `BaseLLMClient` abstract class (Strategy pattern).
    - `GeminiClient` implementation using `google-genai` SDK.
    - `generate()`: sends prompt, returns full text response.
    - `generate_stream()`: yields tokens one by one for streaming.
    - Retry logic with exponential backoff for HTTP 429 rate limits.
    - Lazy singleton via `get_llm_client()`.

---

## Step 12: Prompt Builder
19. Created `backend/llm/prompt_builder.py`:
    - `build_rag_prompt()`: takes a question + retrieved chunks → returns system prompt + user prompt.
    - System prompt: "You are FinRAG, a financial analyst. Only answer from context. Cite with [Source N]."
    - User prompt: numbered source blocks with company, year, and relevance score, followed by the question.

---

## Step 13: RAG Pipeline
20. Created `backend/services/rag_pipeline.py`:
    - `ask()` function: the main orchestrator.
    - Flow: receive question → run semantic search → build prompt → call LLM → return structured `RAGResponse`.
    - `RAGResponse` dataclass: answer, query, sources list, retrieval_time, generation_time, total_time.
    - Added company auto-detection: scans the query for known company names and applies filter automatically.

---

## Step 14: FastAPI Web Server
21. Created `backend/main.py`:
    - FastAPI app with CORS middleware (allows React frontend to connect).
    - Calls `init_db()` on startup.
    - Includes all routers.
    - Health check endpoint at `GET /api/health`.

22. Created `backend/api/schemas.py`:
    - Pydantic models for request/response validation: `AskRequest`, `AskResponse`, `SearchRequest`, `SearchResponse`, `DocumentResponse`, `ChatMessage`, `ChatRequest`.

---

## Step 15: API Endpoints
23. Created `backend/api/routers/documents.py`:
    - `GET /api/documents` — list all documents with metadata.
    - `DELETE /api/documents/{id}` — delete a document and all its chunks.

24. Created `backend/api/routers/upload.py`:
    - `POST /api/upload` — accept PDF via multipart form, run full ingestion pipeline, store in DB.

25. Created `backend/api/routers/search.py`:
    - `POST /api/search` — semantic search only (returns matching chunks).
    - `POST /api/ask` — full RAG (search + LLM answer with citations).
    - `POST /api/ask/stream` — streaming RAG with SSE + chat history support.

---

## Step 16: React Frontend Setup
26. Initialized React app using Vite: `npx create-vite frontend --template react`.
27. Installed and configured Tailwind CSS.
28. Installed `react-router-dom` for client-side routing.
29. Created `frontend/src/App.jsx` — main layout with routes for Dashboard, Upload, and Ask pages.
30. Created `frontend/src/components/Navbar.jsx` — navigation bar with glassmorphism styling.

---

## Step 17: API Client
31. Created `frontend/src/api/client.js`:
    - `fetchDocuments()` — GET all documents.
    - `deleteDocument(id)` — DELETE a document.
    - `uploadDocument(file, metadata)` — POST file upload.
    - `askQuestion(question, filters)` — POST RAG query.
    - `askQuestionStream(question, history, filters, callbacks)` — POST streaming query with SSE parsing.

---

## Step 18: Frontend Pages
32. Created `frontend/src/pages/Dashboard.jsx`:
    - Stats cards showing total documents, chunks, and companies.
    - Data table listing all uploaded documents with delete buttons.
    - Skeleton loaders and fade-in-up entrance animations.

33. Created `frontend/src/pages/Upload.jsx`:
    - Drag-and-drop file upload zone.
    - Metadata inputs for company, year, region.
    - Success/error feedback with animations.

34. Created `frontend/src/pages/AskSearch.jsx`:
    - Full streaming chat interface with user/assistant message bubbles.
    - Company/year/region filter dropdowns.
    - SSE streaming: words appear one by one as the LLM generates.
    - Chat history: stores previous messages and sends them with each new request for follow-up questions.
    - Source chips showing document names and relevance scores.
    - `react-markdown` for formatting LLM responses (tables, lists, bold text).

---

## Step 19: Hybrid Search (BM25 + Vector)
35. Added BM25 sparse retrieval to `backend/engines/search.py` using `rank_bm25`.
36. Implemented Reciprocal Rank Fusion (RRF) to combine BM25 and vector search rankings.
37. Added diversified round-robin retrieval for cross-company queries.

---

## Step 20: Caching
38. Created `backend/engines/cache.py`:
    - In-memory dictionary cache with SHA-256 key hashing.
    - TTL expiration (1 hour) and LRU eviction (max 500 entries).
    - Full cache clear on document upload or delete (invalidation).

---

## Step 21: Streaming & Chat History
39. Added `generate_stream()` to the Gemini LLM client.
40. Created the `POST /api/ask/stream` SSE endpoint that yields tokens using `StreamingResponse`.
41. Frontend reads the stream using `ReadableStream` + `TextDecoder`.
42. Chat history (last 6 messages) is injected into the prompt for follow-up question support.

---

## Step 22: UI Polish
43. Added CSS animations: `fadeInUp`, `scaleIn`, `shimmer`, `cursorBlink`, `progressIndeterminate`.
44. Applied staggered entrance animations to dashboard cards and search results.
45. Added skeleton loaders for all loading states.
46. Added cache-hit badge with glow animation.
47. Added score progress bars on source cards.
48. Added `.markdown-prose` CSS styles for rendering LLM output.

---

## Final File Count

| Layer | Files |
|-------|-------|
| Config & Setup | 4 (`config.py`, `logging.py`, `.env`, `requirements.txt`) |
| Data Pipeline | 5 (`pdf_extractor.py`, `text_cleaner.py`, `chunker.py`, `table_extractor.py`, `ingest.py`) |
| Database | 2 (`database.py`, `models.py`) |
| Engines | 3 (`embedder.py`, `search.py`, `cache.py`) |
| LLM | 2 (`llm_client.py`, `prompt_builder.py`) |
| Services | 1 (`rag_pipeline.py`) |
| API | 4 (`main.py`, `schemas.py`, `documents.py`, `upload.py`, `search.py`) |
| Frontend | 5 (`App.jsx`, `Navbar.jsx`, `Dashboard.jsx`, `Upload.jsx`, `AskSearch.jsx`, `client.js`) |
| **Total** | **~26 core files** |

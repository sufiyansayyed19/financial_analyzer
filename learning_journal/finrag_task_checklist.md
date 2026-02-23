# 📋 FinRAG: Complete Task Checklist (High-Level)

*A sequential list of every single technical task executed to build the FinRAG pipeline from scratch, Phase 1 to Phase 9. No deep theory, just pure action items.*

---

## Phase 1: Foundation & Data Ingestion (PDFs)
- [x] Initialized Python project structure (`backend/core`, `pipelines/`, `api/`).
- [x] Created `config.py` using Pydantic `BaseSettings` for `.env` management.
- [x] Configured structured colored logging using the `rich` library.
- [x] Wrote `pdf_extractor.py` using `PyMuPDF` to rip raw text from 21 financial PDFs.
- [x] Wrote `text_cleaner.py` (a 10-step regex pipeline to remove headers, fix ligatures `ﬁ→fi`, strip page numbers).
- [x] Implemented a frequency-based auto-detector to delete highly repeated header/footer lines.
- [x] Wrote `chunker.py` using a sliding window strategy (1000 chars, 200 overlap) splitting on paragraph/sentence boundaries.
- [x] Wrote `table_extractor.py` to pull structured tables from PDFs into JSON/Markdown format.
- [x] Optimized PyMuPDF table extraction with a line-count pre-calculation heuristic (reducing time from 15m to 57s).
- [x] Wrote `ingest.py` to orchestrate extraction, cleaning, and chunking into an idempotent data pipeline.
- [x] Ran the full pipeline, generating 24,948 cleaned `.txt`, `.json`, and `.md` chunks stored locally.

## Phase 2: Embeddings & Vector Database
- [x] Installed `sentence-transformers` and `SQLAlchemy`.
- [x] Created `backend/db/database.py` to initialize an SQLite database engine.
- [x] Created `backend/db/models.py` defining the `Document` and `Chunk` ORM relational tables.
- [x] Denormalized the ORM by adding `company`, `year`, and `region` directly to the `Chunk` table for fast search filtering.
- [x] Wrote `backend/engines/embedder.py` wrapping the `all-MiniLM-L6-v2` HuggingFace embedding model (384 dimensions).
- [x] Edited SQLite connection to use `PRAGMA journal_mode=WAL` for concurrent read/write capabilities.
- [x] Wrote `store_embeddings.py` to load all 24k chunks from JSON, convert text to vectors in batches, and insert into SQLite.
- [x] Encoded the floating-point vector arrays into raw binary bytes `(*.tobytes())` for fast database storage.
- [x] Wrote `engines/search.py` implementing Cosine Similarity (`np.dot`) mathematically over the in-memory numpy arrays.

## Phase 3: The LLM RAG Pipeline
- [x] Installed `google-genai` SDK and added `GEMINI_API_KEY` to the `.env` file.
- [x] Wrote `backend/llm/llm_client.py` using the Strategy Pattern (`BaseLLMClient` interface).
- [x] Implemented the `GeminiClient` class with exponential backoff retry-logic for HTTP 429 rate limits.
- [x] Wrote `prompt_builder.py` defining the System Persona (financial analyst) and strict grounding rules.
- [x] Implemented automatic citation formatting (`[Source 1]`, `[Source 2]`) injected into the User Prompt.
- [x] Wrote `backend/services/rag_pipeline.py` (The Orchestrator) to tie Search -> Prompt Engineering -> LLM Generation.
- [x] Created the `RAGResponse` Dataclass to structure the answer, source list, and latency timings.
- [x] Tested full end-to-end Python queries against the pipeline.

## Phase 5: Fast API Web Server
- [x] Installed `fastapi` and `uvicorn`.
- [x] Created `backend/main.py` configuring the FastAPI app and CORS middleware for frontend communication.
- [x] Created `backend/api/schemas.py` defining strictly typed Pydantic models for incoming requests/responses.
- [x] Created `routers/documents.py` defining `GET /api/documents` to list all stored files in the DB.
- [x] Implemented `DELETE /api/documents/{id}` to remove a file and cascade-delete its embedded chunks.
- [x] Created `routers/upload.py` defining a MultipartForm `POST /api/upload` endpoint to ingest fresh PDFs live through the API.
- [x] Created `routers/search.py` defining `POST /api/search` (raw semantic search) and `POST /api/ask` (full RAG generation).

## Phase 7: React & Vite Frontend
- [x] Initialized a React SPA project using Vite.
- [x] Installed and configured Tailwind CSS for styling.
- [x] Built the UI scaffolding: `App.jsx`, `Navbar.jsx`, and set up `react-router-dom`.
- [x] Wrote `api/client.js` to create standard JavaScript `fetch()` wrappers to talk to the FastAPI backend.
- [x] Built `Dashboard.jsx`: Data table showing all uploaded documents, stats cards, and file deletion buttons.
- [x] Built `Upload.jsx`: Drag-and-drop file upload zone hooking up to the `/api/upload` backend endpoint.
- [x] Built `AskSearch.jsx` (V1): Basic query input, company/year filter dropdowns, search results list, and static LLM answer box.
- [x] Fixed CORS issues between `localhost:5173` (React) and `localhost:8000` (FastAPI).

## Phase 9: Advanced Optimization & UX
- [x] Implemented BM25 Sparse Retrieval using `rank_bm25` in Python.
- [x] Combined Dense Vectors and BM25 using the Reciprocal Rank Fusion (RRF) algorithm to create true **Hybrid Search**.
- [x] Added Query Auto-Detection (Regex matching company names in user questions to automatically set SQL filters).
- [x] Added Diversified Round-Robin retrieval to pull chunks evenly across multiple companies when no specific filter is set.
- [x] Built an In-Memory Dictionary Cache (`backend/engines/cache.py`) using SHA-256 hashes of queries/filters.
- [x] Added LRU (max 500) and TTL (expire 3600s) eviction rules to the cache.
- [x] Connected Cache Invalidation hooks to the Upload/Delete API endpoints to prevent serving stale financial data.
- [x] Switched Gemini API calls from `generate_content` to `generate_content_stream()`.
- [x] Rewrote `/api/ask` to `StreamingResponse` yielding Server-Sent Events (SSE).
- [x] Rewrote frontend JS fetch logic to use a `ReadableStream` and `TextDecoder` to display words instantly as they arrive.
- [x] Upgraded `AskSearch.jsx` into a Chat interface maintaining an array of Previous Messages (`Chat History`).
- [x] Injected Chat History transcript into the backend LLM Prompt to enable dynamic follow-up questions.
- [x] Installed `react-markdown` to format LLM output (tables, lists, bolding) using CSS Prose styles.
- [x] Added UX Polish: Skeleton loading shimmer cards, staggered CSS fade-in-up animations, and automatic chat scrolling.
- [x] Compiled comprehensive Learning Journals and Interview Prep materials.

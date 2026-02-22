# FinRAG — Project Roadmap & Architecture

> **Financial Document Intelligence Platform**
> Built step-by-step as a learning project

---

## 🧭 What FinRAG Does

```
Financial PDFs → Extract & Clean → Chunk → Embed → Vector Search → RAG (LLM Answers) → Dashboard
```

**Input:** Annual reports from 7 companies (HDFC Bank, Reliance, TCS, JPMorgan, NVIDIA, Pfizer, Walmart)
**Output:** AI-powered Q&A and analytics dashboard over financial data

---

## 🏗️ System Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Frontend   │────▶│   API Layer   │────▶│  Service Layer   │
│   (React)    │◀────│  (FastAPI)    │◀────│  (Orchestration)  │
└─────────────┘     └──────────────┘     └────────┬─────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────┐
                    │                              │                  │
              ┌─────▼─────┐  ┌─────────────┐  ┌───▼────────┐  ┌─────▼─────┐
              │ Pipelines  │  │   Engines    │  │    LLM     │  │  Workers  │
              │ (Ingest)   │  │ (Retrieval)  │  │ (Generate) │  │  (Async)  │
              └─────┬──────┘  └──────┬──────┘  └────────────┘  └───────────┘
                    │                │
              ┌─────▼────────────────▼──────┐
              │     Data Layer              │
              │  SQLite → PostgreSQL+pgvector│
              │  Redis (cache)              │
              └─────────────────────────────┘
```

---

## 📋 Build Phases

### Phase 1: Foundation & PDF Ingestion ✅
- [x] Project scaffolding (folders, config, logging)
- [x] PDF text extraction (PyMuPDF)
- [x] Text cleaning (10-step pipeline with ligature resolution, control char removal, auto-dedup)
- [x] Chunking engine (sliding window with smart boundaries)
- [x] Table extraction (PyMuPDF `find_tables()` with page-skip heuristic)
- [x] End-to-end ingestion (21 PDFs → 24,948 chunks + structured tables)
- [x] Text quality audit (13 checks, 19/21 fully clean)
- [x] Learning journal for Phase 1

### Phase 2: Embeddings & Vector Search ✅
- [x] Embedding engine (`all-MiniLM-L6-v2`, 384 dims, CPU)
- [x] Database layer (SQLAlchemy + SQLite, swappable to PostgreSQL)
- [x] Database models (documents, chunks, tables)
- [x] Vector storage pipeline (23,343 chunks embedded)
- [x] Semantic search engine (cosine similarity, filtered search)
- [x] Learning journal for Phase 2

### Phase 3: RAG Pipeline ✅
- [x] LLM abstraction (Gemini client + Strategy pattern)
- [x] Prompt builder (financial system prompt + citation format)
- [x] RAG pipeline orchestrator (search → prompt → LLM → cited answer)
- [x] Testing (NVIDIA revenue, JPMorgan risks — cited answers)

### Phase 4: Analytics Engine
- [ ] Sentiment analysis
- [ ] Risk classification
- [ ] Theme extraction

### Phase 5: API Layer ✅
- [x] FastAPI app (CORS, routers, Swagger docs)
- [x] Pydantic schemas (auto-validation)
- [x] Document endpoints (upload, list, delete)
- [x] Search endpoints (semantic search, RAG Q&A)

### Phase 6: Caching & Async Workers
- [ ] Redis caching
- [ ] Job queue for ingestion
- [ ] Worker status tracking

### Phase 7: Frontend Dashboard
- [ ] React setup
- [ ] Document upload UI
- [ ] Search & Q&A interface
- [ ] Analytics charts

### Phase 8: Final Summary
- [ ] Complete learning journal
- [ ] Architecture decisions recap

---

## 📂 Project Structure

```
nlp_project/
├── backend/
│   ├── main.py
│   ├── core/           # Config, logging
│   ├── pipelines/      # Ingestion + embedding storage ✅
│   │   ├── pdf_extractor.py      # PDF → text
│   │   ├── text_cleaner.py       # 10-step cleaning
│   │   ├── chunker.py            # Sliding window chunks
│   │   ├── table_extractor.py    # PDF → structured tables
│   │   ├── ingest.py             # Orchestrator (text + tables)
│   │   └── store_embeddings.py   # Embed + store (Phase 2)
│   ├── engines/        # Retrieval + analytics
│   │   ├── embedder.py           # Embedding model (Phase 2)
│   │   └── search.py             # Semantic search (Phase 2)
│   ├── services/       # Business logic
│   ├── api/            # FastAPI routers
│   ├── workers/        # Async jobs
│   ├── llm/            # LLM abstraction
│   └── db/             # Database models
│       ├── database.py           # Engine + sessions (Phase 2)
│       └── models.py             # SQLAlchemy models (Phase 2)
├── data/               # 21 raw PDFs
├── processed/          # Pipeline output (4 files per PDF)
│   └── {region}/annual/{company}/
│       ├── {name}.txt            # Cleaned text
│       ├── {name}_chunks.json    # Text chunks + metadata
│       ├── {name}_tables.json    # Structured table data
│       └── {name}_tables.md      # Markdown tables for LLM
├── learning_journal/   # Phase-by-phase notes
└── requirements.txt
```

---

## 📊 Dataset

| Company | Region | Reports | Years |
|---------|--------|---------|-------|
| HDFC Bank | India | 3 | 2022–2024 |
| Reliance | India | 3 | 2023–2025 |
| TCS | India | 3 | 2023–2025 |
| JPMorgan | US | 3 | 2022–2024 |
| NVIDIA | US | 3 | 2023–2025 |
| Pfizer | US | 3 | 2022–2024 |
| Walmart | US | 3 | 2023–2025 |

**Total:** 21 PDFs, 5,350+ pages, 24,948 chunks

---

## 🧱 Key Design Principles

1. **Separation of concerns** — each module does one thing
2. **Service layer orchestrates** — engines don't call each other
3. **No business logic in routers** — routers are thin
4. **Async where IO-heavy** — file reads, DB queries, LLM calls
5. **Idempotent pipelines** — safe to re-run
6. **No hardcoded secrets** — everything in `.env`
7. **Data-driven cleaning** — let frequency analysis find noise, not hardcoded rules
8. **Pre-check before expensive ops** — skip work that won't produce results

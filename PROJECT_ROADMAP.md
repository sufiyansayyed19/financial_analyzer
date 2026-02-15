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
              │  PostgreSQL + pgvector      │
              │  Redis (cache)              │
              └─────────────────────────────┘
```

---

## 📋 Build Phases

### Phase 1: Foundation & PDF Ingestion ✅
- [x] Project scaffolding (folders, config, logging)
- [x] PDF text extraction (PyMuPDF)
- [x] Text cleaning (9-step pipeline)
- [x] Chunking engine (sliding window)
- [x] End-to-end ingestion (21 PDFs → 24,948 chunks)

### Phase 2: Embeddings & Vector Search
- [ ] Embedding generation (sentence-transformers)
- [ ] PostgreSQL + pgvector setup
- [ ] Database models (SQLAlchemy)
- [ ] Vector storage pipeline
- [ ] Similarity search

### Phase 3: RAG Pipeline
- [ ] LLM abstraction (Local + API clients)
- [ ] Retrieval pipeline (hybrid search)
- [ ] Prompt builder + context assembly
- [ ] Q&A endpoint with citations

### Phase 4: Analytics Engine
- [ ] Sentiment analysis
- [ ] Risk classification
- [ ] Theme extraction

### Phase 5: API Layer & Auth
- [ ] FastAPI routers
- [ ] JWT authentication
- [ ] User-scoped operations

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
│   ├── pipelines/      # Ingestion pipeline ✅
│   ├── engines/        # Retrieval + analytics
│   ├── services/       # Business logic
│   ├── api/            # FastAPI routers
│   ├── workers/        # Async jobs
│   ├── llm/            # LLM abstraction
│   └── db/             # Database models
├── data/               # 21 raw PDFs
├── processed/          # Pipeline output (txt + json chunks)
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

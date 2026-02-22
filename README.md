<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/Tailwind-3-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" />
  <img src="https://img.shields.io/badge/Gemini-AI-8E75B2?style=for-the-badge&logo=google&logoColor=white" />
</p>

# 🏦 FinRAG — Financial Document Intelligence

> **Ask questions about financial reports and get AI-powered answers with source citations.**

FinRAG is a full-stack Retrieval-Augmented Generation (RAG) system built for financial documents. Upload annual reports, 10-K filings, and earnings transcripts — then search semantically or ask natural language questions to get cited, grounded answers.

---

## ✨ Features

- 📄 **PDF Ingestion Pipeline** — Extract, clean, and chunk financial PDFs (10-step text cleaning)
- 🔍 **Semantic Search** — Find relevant passages using sentence embeddings (all-MiniLM-L6-v2)
- 🤖 **RAG Q&A** — Ask questions and get AI answers with `[Source N]` citations via Google Gemini
- 🌐 **REST API** — 6 FastAPI endpoints with auto-generated Swagger docs
- 💻 **React Dashboard** — Dark glassmorphism UI for upload, search, and Q&A
- 📊 **Multi-company Support** — Filter by company, year, and region

---

## 🖥️ Screenshots

<details>
<summary>Dashboard — Document Overview</summary>
<br/>
Stats cards showing document count, total chunks, and system status. Full document table with company, year, and delete controls.
</details>

<details>
<summary>Ask & Search — RAG Q&A</summary>
<br/>
Ask natural language questions with company/year filters. AI answers include timing breakdown and expandable source cards with relevance scores.
</details>

<details>
<summary>Upload — Drag & Drop</summary>
<br/>
Drag-and-drop PDF upload with real-time processing pipeline animation (Extract → Clean → Chunk → Embed → Store).
</details>

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│         Dashboard  •  Ask & Search  •  Upload            │
└───────────────────────┬─────────────────────────────────┘
                        │ REST API (JSON)
┌───────────────────────▼─────────────────────────────────┐
│                   FastAPI Backend                         │
│                                                          │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Document  │  │   Semantic   │  │   RAG Pipeline    │  │
│  │ Ingestion │  │   Search     │  │ Search → LLM →    │  │
│  │ Pipeline  │  │   Engine     │  │ Cited Answer      │  │
│  └────┬─────┘  └──────┬───────┘  └────────┬──────────┘  │
│       │               │                    │             │
│  ┌────▼───────────────▼────────────────────▼──────────┐  │
│  │              SQLite + Embeddings                    │  │
│  │         (Documents, Chunks, Vectors)                │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Google Gemini API Key](https://aistudio.google.com/apikey) (free tier works)

### 1. Clone & Setup Backend

```bash
git clone https://github.com/sufiyansayyed19/financial_analyzer.git
cd financial_analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional (defaults shown)
LLM_MODEL=gemini-2.5-flash
LLM_TEMPERATURE=0.3
EMBEDDING_MODEL=all-MiniLM-L6-v2
TOP_K_RESULTS=5
APP_NAME=FinRAG
```

### 3. Setup Frontend

```bash
cd frontend
npm install
```

### 4. Run

```bash
# Terminal 1: Backend (from project root)
uvicorn backend.main:app --port 8000

# Terminal 2: Frontend (from frontend/)
cd frontend
npm run dev
```

Open **http://localhost:5173** and you're ready! 🎉

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | System status + document/chunk counts |
| `GET` | `/api/documents` | List all processed documents |
| `POST` | `/api/upload` | Upload PDF → full ingestion pipeline |
| `POST` | `/api/search` | Semantic search with filters |
| `POST` | `/api/ask` | RAG Q&A with source citations |
| `DELETE` | `/api/documents/{id}` | Delete document and its chunks |

Interactive docs at **http://localhost:8000/docs** (Swagger UI).

### Example: Ask a Question

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What was NVIDIA revenue in 2024?", "company": "nvidia"}'
```

```json
{
  "answer": "NVIDIA's total revenue for fiscal year 2024 was $60.9 billion, representing a 126% increase year-over-year [Source 1]...",
  "sources": [
    {"source_id": 1, "company": "nvidia", "year": "2024", "relevance_score": 0.82}
  ],
  "retrieval_time": 1.2,
  "generation_time": 5.1,
  "total_time": 6.3
}
```

---

## 📁 Project Structure

```
financial_analyzer/
├── backend/
│   ├── main.py                  # FastAPI app (CORS, routers, startup)
│   ├── api/
│   │   ├── schemas.py           # Pydantic request/response models
│   │   └── routers/
│   │       ├── documents.py     # Upload, list, delete endpoints
│   │       └── search.py        # Search & RAG Q&A endpoints
│   ├── core/
│   │   └── config.py            # App settings (env vars)
│   ├── db/
│   │   ├── models.py            # SQLAlchemy models (Document, Chunk)
│   │   └── session.py           # Database connection
│   ├── engines/
│   │   ├── embedder.py          # Sentence-transformers embeddings
│   │   └── search.py            # Semantic search with cosine similarity
│   ├── llm/
│   │   ├── llm_client.py        # Gemini API client (Strategy pattern)
│   │   └── prompt_builder.py    # Financial-domain prompt templates
│   ├── pipelines/
│   │   └── ingestion.py         # PDF → text → clean → chunk → embed
│   └── services/
│       └── rag_pipeline.py      # RAG orchestrator (search → prompt → LLM)
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Router + layout
│   │   ├── api/client.js        # API fetch wrappers
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx    # Stats + document table
│   │   │   ├── AskSearch.jsx    # Q&A + search interface
│   │   │   └── Upload.jsx       # Drag-and-drop upload
│   │   └── components/
│   │       └── Navbar.jsx       # Navigation bar
│   └── tailwind.config.js       # Dark theme configuration
├── learning_journal/            # Development notes & concepts
├── data/                        # Raw PDF files
├── requirements.txt
└── .env                         # API keys (not tracked)
```

---

## 🧠 How It Works

### Ingestion Pipeline (Upload)
```
PDF → PyMuPDF Extract → 10-Step Text Cleaning → Smart Chunking (512 tokens)
    → Sentence Embeddings (all-MiniLM-L6-v2) → SQLite Storage
```

### RAG Pipeline (Ask)
```
Question → Embed Query → Cosine Similarity Search → Top-K Chunks
    → Financial Prompt Template → Gemini API → Cited Answer
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, Vite 7, Tailwind CSS 3 |
| **Backend** | FastAPI, Uvicorn, Pydantic |
| **NLP** | Sentence-Transformers (all-MiniLM-L6-v2) |
| **LLM** | Google Gemini (gemini-2.5-flash) |
| **Database** | SQLite + SQLAlchemy |
| **PDF Processing** | PyMuPDF (fitz) |

---

## 📝 Learning Journal

This project was built as a learning exercise. Detailed notes on concepts, challenges, and design decisions are in the [`learning_journal/`](./learning_journal/) directory:

- **Phase 1** — PDF extraction, text cleaning, chunking strategies
- **Phase 2** — Sentence embeddings, cosine similarity, semantic search
- **Phase 3** — RAG pipeline, prompt engineering, LLM integration
- **Phase 5** — FastAPI, Pydantic schemas, CORS, REST API design
- **Phase 7** — React, Vite, Tailwind CSS, component architecture

---

## 📄 License

This project is for educational purposes.

---

<p align="center">
  Built with ☕ by <a href="https://github.com/sufiyansayyed19">Sufiyan Sayyed</a>
</p>

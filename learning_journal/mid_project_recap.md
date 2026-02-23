# FinRAG: End-to-End Project Architecture & Interview Guide
*A comprehensive step-by-step summary of the architecture, tech stack, and features built for FinRAG.*

This document serves as your "Interview Cheat Sheet." If an interviewer asks, *"Walk me through a complex AI project you built,"* this is your script.

---

## 🎯 The Elevator Pitch
**"I built FinRAG, an end-to-end Retrieval-Augmented Generation (RAG) system for financial analysis. It allows users to upload dense, 100+ page financial PDFs (like 10-Ks or Annual Reports), processes them into a vector database, and provides a real-time, streaming chat interface. The system uses a Hybrid Search approach combining vector embeddings and BM25 to achieve high precision, and it grounds every AI answer with exact source citations to prevent hallucinations."**

---

## 🛠️ Tech Stack
* **Backend:** Python, FastAPI, Uvicorn
* **Database & ORM:** SQLite, SQLAlchemy
* **AI / ML Models:** 
  * **Embeddings:** `all-MiniLM-L6-v2` (SentenceTransformers, HuggingFace)
  * **LLM:** Google Gemini (`google-genai` SDK)
* **Data Ingestion:** `PyMuPDF` (PDF parsing), `rank_bm25` (Sparse retrieval)
* **Frontend:** React, Vite, Tailwind CSS, Server-Sent Events (SSE)

---

## 🏗️ Step-by-Step Implementation Process

### Step 1: Data Ingestion & Chunking (The Foundation)
You cannot pass a 100-page PDF directly to an LLM. It exceeds the context window and dilutes focus.
1. **Extraction:** Used `PyMuPDF` to read raw text from uploaded PDFs, skipping blank pages.
2. **Cleaning:** Built a text pipeline to normalize whitespace, remove ligatures, and drop irrelevant tiny lines.
3. **Sliding Window Chunking:** Split the cleaned text into ~1000-character blocks with a 200-character overlap. 
   * *Interview Talking Point:* "The overlap is crucial. If a sentence explaining 'NVIDIA's revenue' spans across a hard cutoff, both chunks lose context. The 200-character overlap ensures context is preserved across boundaries."

### Step 2: Vectorization & Database (The Knowledge Base)
To make text searchable by *meaning*, it must be converted into math (vectors).
1. **Embeddings:** Passed every chunk through `SentenceTransformers` to generate a 384-dimensional dense vector.
2. **Relational Storage:** Used `SQLAlchemy` and `SQLite` to store the data. 
   * **Documents Table:** Stores metadata (Company, Year, Region).
   * **Chunks Table:** Stores the raw text, the parent Document ID, and the binary-encoded vector blob.

### Step 3: Hybrid Search Retrieval (The Engine)
When a user asks a question, how do we find the right paragraphs?
1. **Vector Search (Dense):** Converts the user's question into a vector and calculates **Cosine Similarity** against all chunks in the DB. Great for "semantic" meaning (e.g., "money" matches "revenue").
2. **BM25 Search (Sparse):** Great for exact keyword matching (e.g., specific part numbers, "EPS", or acronyms).
3. **Reciprocal Rank Fusion (RRF):** Combined both algorithms. RRF looks at the rank of a chunk in both lists and assigns a penalty-based blended score `1/(k+rank)`.
   * *Interview Talking Point:* "RAG systems often fail because vector search misses exact keywords. By combining Semantic Search (Vector) with Keyword Search (BM25) via RRF, I drastically improved retrieval accuracy for specific financial terminology."

### Step 4: The RAG Generation Pipeline (The Brain)
Once we have the top 5 most relevant chunks from Step 3, we generate the answer.
1. **Prompt Engineering:** Injected the retrieved chunks into a strict system prompt.
2. **Grounding:** explicitly instructed the LLM (Gemini) to *only* use the provided context and to cite its sources using `[Source N]` tags.
3. **Smart Company Detection:** Built a query parser that detects company names in the user's question and auto-filters the database search to that specific company.
   * *Interview Talking Point:* "If a user asks 'Compare revenues', the system uses round-robin diversified retrieval across all companies. But if they ask 'Revenue of TCS', my regex-based auto-detector catches 'TCS' and automatically applies a SQL filter, preventing query dilution."

### Step 5: Advanced Optimization (Production Readiness)
To make the app feel like a real product (fast and cheap), I implemented:
1. **In-Memory Caching:** Built a dictionary-based TTL cache. It hashes the user's normalized query and filters. If there is a cache hit, the response returns in 0.001s, saving a 5-second API call and lowering costs.
2. **Cache Invalidation:** Hooked the cache to the Document Upload/Delete endpoints so stale answers are immediately wiped when the underlying data changes.
3. **Server-Sent Events (SSE) Streaming:** Instead of making the user wait 8 seconds for the full LLM payload, the backend yields tokens using `StreamingResponse`. The React frontend parses the stream and updates the UI word-by-word instantly.
4. **Conversational Memory:** Passed the last 3 turns of the chat history back to the backend, injecting it into the prompt.
   * *Interview Talking Point:* "Standard RAG is stateless. I added conversational memory by injecting the chat history transcript into the context window, allowing the LLM to successfully answer follow-up questions with pronoun resolution like 'What about *their* risks?'"

### Step 6: Frontend Polish (The User Experience)
1. **React SPA:** Built a rapid Single Page Application with dynamic routing.
2. **Markdown Parsing:** Used `react-markdown` to format LLM outputs beautifully (tables, bolding, code blocks).
3. **Micro-Interactions:** Added "skeleton shimmer" loading states, fade-in-up staggered entrance animations, and dynamic source chips showing relevance scores.

---

## 📈 Summary of Achievements
You took a raw PDF and transformed it into a fully conversational, real-time, streaming AI agent with exact citations, hybrid search, and caching. You handled the data engineering, the AI pipeline, the backend API, and the frontend UX. 

**This is a complete Full-Stack AI Engineer portfolio piece.**

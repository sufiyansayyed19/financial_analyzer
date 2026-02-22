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

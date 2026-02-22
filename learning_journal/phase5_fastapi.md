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

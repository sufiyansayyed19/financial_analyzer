"""
🧠 FinRAG — FastAPI Application
==================================

WHAT THIS DOES:
---------------
The main entry point for the FinRAG API server.

FASTAPI CONCEPTS:
──────────────────
- APP: The FastAPI application instance
- ROUTERS: Groups of related endpoints (like blueprints in Flask)
- CORS: Allows the React frontend to talk to this API
- STARTUP: Code that runs when the server starts

RUN THE SERVER:
  cd "d:\\New folder\\nlp_project"
  venv\\Scripts\\uvicorn backend.main:app --reload --port 8000

EXPLORE THE API:
  http://localhost:8000/docs     ← Swagger interactive docs
  http://localhost:8000/redoc    ← Alternative docs

WHAT YOU'LL LEARN:
- FastAPI application setup
- CORS middleware (why and how)
- Router composition
- Startup events for initialization
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routers import documents, search
from backend.api.schemas import HealthResponse
from backend.core.config import settings
from backend.core.logging import get_logger
from backend.db.database import get_session, init_db
from backend.db.models import Chunk, Document

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# 🚀 CREATE APP
# ──────────────────────────────────────────────

app = FastAPI(
    title="FinRAG API",
    description=(
        "Financial Retrieval-Augmented Generation API. "
        "Upload financial PDFs, search by meaning, and get "
        "AI-generated answers with source citations."
    ),
    version="1.0.0",
)


# ──────────────────────────────────────────────
# 🔓 CORS MIDDLEWARE
# ──────────────────────────────────────────────
# CORS (Cross-Origin Resource Sharing) controls
# which websites can call this API.
#
# Without CORS: React app at localhost:3000
# CANNOT call API at localhost:8000 (browser blocks it).
#
# With CORS: We explicitly allow localhost:3000.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# 📦 REGISTER ROUTERS
# ──────────────────────────────────────────────
# Routers group related endpoints.
# This keeps the main file clean.

app.include_router(documents.router)
app.include_router(search.router)


# ──────────────────────────────────────────────
# ⚡ STARTUP EVENT
# ──────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Initialize database on server start."""
    init_db()
    logger.info(f"🚀 {settings.app_name} API started!")


# ──────────────────────────────────────────────
# ❤️ HEALTH CHECK
# ──────────────────────────────────────────────

@app.get(
    "/api/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["system"],
)
async def health():
    """Check if the API is running and return database stats."""
    session = get_session()
    try:
        doc_count = session.query(Document).count()
        chunk_count = session.query(Chunk).count()
    finally:
        session.close()

    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        total_documents=doc_count,
        total_chunks=chunk_count,
    )


# ──────────────────────────────────────────────
# 🧪 CLI ENTRY POINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

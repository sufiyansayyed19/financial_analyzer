"""
🧠 FinRAG — Search Router
============================

ENDPOINTS:
  POST /api/search  → Semantic search (returns chunks)
  POST /api/ask     → RAG Q&A (returns LLM answer with citations)

WHY POST INSTEAD OF GET?
─────────────────────────
Search is traditionally GET, but:
- Our search has complex filters (company, year, region)
- Query strings get messy: /search?q=long+query&company=nvidia&year=2024
- POST with JSON body is cleaner and more extensible
- Modern APIs (Elasticsearch, OpenAI) use POST for search too

WHAT YOU'LL LEARN:
- POST endpoints for search operations
- Connecting API to service layer
- Response formatting for frontend consumption
"""

from fastapi import APIRouter

from backend.api.schemas import (
    AskRequest,
    AskResponse,
    SearchRequest,
    SearchResponse,
    SearchResultResponse,
    SourceResponse,
)
from backend.core.logging import get_logger
from backend.engines.search import search as semantic_search
from backend.services.rag_pipeline import ask as rag_ask

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["search"])


# ──────────────────────────────────────────────
# 🔍 SEMANTIC SEARCH
# ──────────────────────────────────────────────

@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search over documents",
)
async def search(request: SearchRequest):
    """
    Search for relevant text chunks using semantic similarity.

    Returns raw chunks ranked by relevance — useful for:
    - Browsing related content
    - Finding specific passages
    - Building custom prompts

    For AI-generated answers, use /api/ask instead.
    """
    results = semantic_search(
        query=request.query,
        top_k=request.top_k,
        company=request.company,
        year=request.year,
        region=request.region,
    )

    return SearchResponse(
        query=request.query,
        results=[
            SearchResultResponse(
                text=r.text,
                score=round(r.score, 4),
                company=r.company,
                year=r.year,
                region=r.region,
                chunk_index=r.chunk_index,
            )
            for r in results
        ],
        total_results=len(results),
    )


# ──────────────────────────────────────────────
# 🤖 RAG Q&A
# ──────────────────────────────────────────────

@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a question (RAG with citations)",
)
async def ask(request: AskRequest):
    """
    Ask a question and get an AI-generated answer with source citations.

    This is the MAIN feature of FinRAG:
    1. Searches for relevant document chunks
    2. Sends them as context to Gemini
    3. Returns an answer grounded in your data with [Source N] citations
    """
    response = rag_ask(
        question=request.question,
        company=request.company,
        year=request.year,
        region=request.region,
        top_k=request.top_k,
    )

    return AskResponse(
        answer=response.answer,
        query=response.query,
        sources=[
            SourceResponse(**s)
            for s in response.sources
        ],
        retrieval_time=response.retrieval_time,
        generation_time=response.generation_time,
        total_time=response.total_time,
        chunks_searched=response.chunks_searched,
    )

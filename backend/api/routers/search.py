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
from fastapi.responses import StreamingResponse

from backend.api.schemas import (
    AskRequest,
    AskResponse,
    ChatRequest,
    SearchRequest,
    SearchResponse,
    SearchResultResponse,
    SourceResponse,
)
from backend.core.config import settings
from backend.core.logging import get_logger
from backend.engines.cache import rag_cache
from backend.engines.search import search as semantic_search
from backend.llm.llm_client import get_llm_client
from backend.llm.prompt_builder import build_rag_prompt
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
# 🤖 RAG Q&A (Non-streaming, kept for backward compatibility)
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


# ──────────────────────────────────────────────
# 🚀 STREAMING RAG Q&A (with Chat History)
# ──────────────────────────────────────────────

@router.post(
    "/ask/stream",
    summary="Ask with streaming response + chat history",
)
async def ask_stream(request: ChatRequest):
    """
    Streaming RAG endpoint with conversational memory.

    HOW STREAMING WORKS:
    ─────────────────────
    Instead of waiting for the full LLM response (3-8 seconds),
    this endpoint sends text chunks as they arrive from Gemini.

    Uses Server-Sent Events (SSE) format:
      data: {"type": "sources", "sources": [...]}
      data: {"type": "token", "token": "The"}
      data: {"type": "token", "token": " revenue"}
      data: {"type": "done"}

    HOW CHAT HISTORY WORKS:
    ────────────────────────
    The frontend sends previous messages in request.history.
    We inject them into the prompt so the LLM can reference
    earlier questions and answers for follow-up queries.
    """
    import json
    import time

    top_k = request.top_k
    company_filter = request.company

    # Auto-detect company from query (same logic as rag_pipeline.ask)
    if not company_filter:
        from backend.db.database import get_session
        from backend.db.models import Document
        session = get_session()
        try:
            known_companies = [
                r[0] for r in session.query(Document.company).distinct().all()
            ]
        finally:
            session.close()

        query_lower = request.question.lower()
        for c in known_companies:
            if f" {c}" in f" {query_lower} " or f" {c}'s" in f" {query_lower} ":
                company_filter = c
                logger.info(f"🎯 Stream: Auto-detected company: '{c}' from query")
                break

    if not company_filter and top_k < 10:
        top_k = 10

    def event_stream():
        total_start = time.time()

        # Step 1: Retrieve relevant chunks
        search_results = semantic_search(
            query=request.question,
            top_k=top_k,
            company=company_filter,
            year=request.year,
            region=request.region,
        )
        retrieval_time = time.time() - total_start

        # Step 2: Build sources metadata and send it first
        sources = [
            {
                "source_id": i + 1,
                "company": r.company,
                "year": r.year,
                "region": r.region,
                "relevance_score": round(r.score, 3),
                "chunk_preview": r.text[:100] + "...",
            }
            for i, r in enumerate(search_results)
        ]

        yield f"data: {json.dumps({'type': 'sources', 'sources': sources, 'retrieval_time': round(retrieval_time, 3)})}\n\n"

        if not search_results:
            yield f"data: {json.dumps({'type': 'token', 'token': 'No relevant documents found.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'total_time': round(time.time() - total_start, 3)})}\n\n"
            return

        # Step 3: Build prompt (with chat history injected)
        system_prompt, user_prompt = build_rag_prompt(request.question, search_results)

        # Inject conversation history into the prompt
        if request.history:
            history_text = "\n\nPREVIOUS CONVERSATION:\n"
            for msg in request.history[-6:]:  # Keep last 6 messages (3 turns)
                role_label = "User" if msg.role == "user" else "Assistant"
                history_text += f"{role_label}: {msg.content}\n"
            history_text += "\n(Use the above conversation for context on follow-up questions.)\n"
            user_prompt = history_text + user_prompt

        # Step 4: Stream the LLM response token by token
        gen_start = time.time()
        client = get_llm_client()

        for token in client.generate_stream(user_prompt, system_prompt=system_prompt):
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

        generation_time = time.time() - gen_start
        total_time = time.time() - total_start

        logger.info(
            f"✅ Streamed answer in {total_time:.1f}s "
            f"(retrieve={retrieval_time:.2f}s, generate={generation_time:.2f}s)"
        )

        yield f"data: {json.dumps({'type': 'done', 'total_time': round(total_time, 3), 'generation_time': round(generation_time, 3)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


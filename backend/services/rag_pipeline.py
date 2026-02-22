"""
🧠 FinRAG — RAG Pipeline
===========================

WHAT THIS DOES:
---------------
This is the ORCHESTRATOR — the "brain" that connects all the pieces:
  Search (Phase 2) + Prompt Builder + LLM Client = Intelligent Answers

RAG PIPELINE FLOW:
───────────────────
  User: "What was NVIDIA's revenue in 2024?"
    │
    ▼ Step 1: RETRIEVE
    search(query, top_k=5) → relevant chunks with scores
    │
    ▼ Step 2: AUGMENT
    build_rag_prompt(query, chunks) → structured prompt with context
    │
    ▼ Step 3: GENERATE
    llm_client.generate(prompt) → answer with citations
    │
    ▼ Step 4: PACKAGE
    RAGResponse(answer, sources, timings) → structured response

WHY RAG BEATS PLAIN LLM:
──────────────────────────
Plain LLM:  "What was NVIDIA's 2024 revenue?" → May hallucinate or be outdated
RAG:        "What was NVIDIA's 2024 revenue?" → Finds actual data → accurate answer

RAG grounds the LLM in REAL DATA from your documents.
The LLM can only use what we provide — no hallucination.

WHAT YOU'LL LEARN:
- Service layer orchestration pattern
- Connecting multiple subsystems cleanly
- Performance logging (timing each step)
- Structured response objects
"""

import time
from dataclasses import dataclass, field

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.engines.search import SearchResult, search
from backend.llm.llm_client import get_llm_client
from backend.llm.prompt_builder import build_rag_prompt

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# 📦 RESPONSE DATACLASS
# ──────────────────────────────────────────────

@dataclass
class RAGResponse:
    """
    The complete response from a RAG query.

    Contains the answer, sources used, and timing information.
    This is what the API will return to the frontend.
    """

    # The LLM-generated answer
    answer: str

    # The original question
    query: str

    # Sources used (for citation display)
    sources: list[dict] = field(default_factory=list)

    # Timing breakdown (for debugging/optimization)
    retrieval_time: float = 0.0
    generation_time: float = 0.0
    total_time: float = 0.0

    # How many chunks were searched
    chunks_searched: int = 0


# ──────────────────────────────────────────────
# 🚀 MAIN RAG FUNCTION
# ──────────────────────────────────────────────

def ask(
    question: str,
    company: str | None = None,
    year: str | None = None,
    region: str | None = None,
    top_k: int | None = None,
) -> RAGResponse:
    """
    Ask a question and get an AI-generated answer with citations.

    This is the MAIN entry point for the RAG system.
    Everything flows through this function.

    Args:
        question: Natural language question about financial documents
        company: Optional filter (e.g., "nvidia", "jpmorgan")
        year: Optional filter (e.g., "2024")
        region: Optional filter (e.g., "us", "india")
        top_k: How many chunks to retrieve (default from config)

    Returns:
        RAGResponse with answer, sources, and timings

    Example:
        >>> response = ask("What was NVIDIA's revenue in 2024?")
        >>> print(response.answer)
        "According to the annual report, NVIDIA's revenue..."
        >>> print(response.sources)
        [{"company": "nvidia", "year": "2024", "score": 0.72}]
    """
    if top_k is None:
        top_k = settings.rag_top_k

    total_start = time.time()
    filter_desc = ""
    if company:
        filter_desc += f" company={company}"
    if year:
        filter_desc += f" year={year}"

    logger.info(f"❓ Question: {question}")
    if filter_desc:
        logger.info(f"   Filters:{filter_desc}")

    # ── Step 1: RETRIEVE ──
    # Search for relevant chunks using semantic search
    retrieve_start = time.time()
    search_results: list[SearchResult] = search(
        query=question,
        top_k=top_k,
        company=company,
        year=year,
        region=region,
    )
    retrieval_time = time.time() - retrieve_start

    logger.info(
        f"📚 Retrieved {len(search_results)} chunks in {retrieval_time:.2f}s"
    )

    if not search_results:
        return RAGResponse(
            answer="I couldn't find any relevant documents matching your query. "
                   "Try broadening your search or checking the available documents.",
            query=question,
            sources=[],
            retrieval_time=retrieval_time,
            total_time=time.time() - total_start,
        )

    # ── Step 2: AUGMENT ──
    # Build the prompt with context from search results
    system_prompt, user_prompt = build_rag_prompt(question, search_results)

    # ── Step 3: GENERATE ──
    # Send to LLM and get the answer
    gen_start = time.time()
    client = get_llm_client()
    answer = client.generate(user_prompt, system_prompt=system_prompt)
    generation_time = time.time() - gen_start

    # ── Step 4: PACKAGE ──
    # Build structured response with source citations
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

    total_time = time.time() - total_start

    logger.info(
        f"✅ Answer generated in {total_time:.1f}s "
        f"(retrieve={retrieval_time:.2f}s, generate={generation_time:.2f}s)"
    )

    return RAGResponse(
        answer=answer,
        query=question,
        sources=sources,
        retrieval_time=round(retrieval_time, 3),
        generation_time=round(generation_time, 3),
        total_time=round(total_time, 3),
        chunks_searched=len(search_results),
    )


# ──────────────────────────────────────────────
# 🖨️ PRETTY PRINT
# ──────────────────────────────────────────────

def ask_pretty(question: str, **kwargs) -> RAGResponse:
    """
    Ask a question and print the response beautifully.

    Useful for interactive testing and demos.
    """
    print(f"\n{'='*60}")
    print(f"❓ {question}")
    print(f"{'='*60}\n")

    response = ask(question, **kwargs)

    print(f"🤖 Answer:\n{response.answer}")

    print(f"\n{'─'*60}")
    print(f"📚 Sources ({len(response.sources)}):")
    for s in response.sources:
        print(
            f"   [{s['source_id']}] {s['company'].upper()} {s['year']} "
            f"(relevance: {s['relevance_score']:.3f})"
        )

    print(f"\n⏱️  Timing:")
    print(f"   Retrieval:   {response.retrieval_time:.2f}s")
    print(f"   Generation:  {response.generation_time:.2f}s")
    print(f"   Total:       {response.total_time:.2f}s")
    print(f"{'='*60}")

    return response


# ──────────────────────────────────────────────
# 🧪 CLI ENTRY POINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    print("\n" + "=" * 60)
    print("🧪 FinRAG — RAG PIPELINE TEST")
    print("=" * 60)

    # Default test questions
    questions = [
        ("What was NVIDIA's total revenue in fiscal year 2024?", {"company": "nvidia"}),
        ("What are JPMorgan's key risk factors?", {"company": "jpmorgan"}),
        ("Compare the dividend policies across Indian companies", {"region": "india"}),
    ]

    # Or use command-line argument
    if len(sys.argv) > 1:
        custom_q = " ".join(sys.argv[1:])
        questions = [(custom_q, {})]

    for question, filters in questions:
        ask_pretty(question, **filters)
        print("\n")

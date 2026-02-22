"""
🧠 FinRAG — Prompt Builder
============================

WHAT THIS DOES:
---------------
Assembles the RAG prompt: context chunks + user question → structured prompt.

WHY PROMPT ENGINEERING MATTERS:
────────────────────────────────
The same LLM can give wildly different answers depending on HOW you ask.
A good RAG prompt must:
  1. Tell the LLM its role (financial analyst)
  2. Provide the retrieved context (our search results)
  3. Ask the question clearly
  4. Instruct it to cite sources
  5. Tell it to say "I don't know" when data is insufficient

BAD PROMPT (no structure):
  "Here's some text: {chunks}. What was the revenue?"

GOOD PROMPT (structured):
  "You are a financial analyst. Based on these excerpts from
   annual reports [Source 1: NVIDIA 2024]..., answer: What was
   the revenue? Cite your sources using [Source N]."

WHAT YOU'LL LEARN:
- Prompt template design for RAG
- Context window management
- Source citation formatting
- How prompt structure affects LLM output quality
"""

from dataclasses import dataclass

from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# 📝 SYSTEM PROMPT
# ──────────────────────────────────────────────
# This tells the LLM WHO it is and HOW to behave.
# Think of it as the LLM's "job description".

SYSTEM_PROMPT = """You are FinRAG, an expert financial analyst AI assistant.

YOUR ROLE:
- Answer questions about financial documents (annual reports, 10-K filings)
- Provide accurate, factual answers based ONLY on the provided context
- Always cite your sources using [Source N] notation

RULES:
1. ONLY use information from the provided context excerpts
2. If the context doesn't contain enough information, say "Based on the available documents, I don't have sufficient information to answer this question."
3. Always cite which source(s) you used: [Source 1], [Source 2], etc.
4. When discussing financial figures, include the exact numbers from the source
5. Be concise but thorough — aim for 2-4 paragraphs
6. If multiple sources provide different data points, synthesize them together"""


# ──────────────────────────────────────────────
# 📄 CONTEXT FORMATTING
# ──────────────────────────────────────────────

@dataclass
class FormattedContext:
    """
    The formatted context ready to inject into a prompt.

    Attributes:
        text: The full formatted context string
        num_sources: How many sources were included
        total_chars: Total character count (for token estimation)
    """
    text: str
    num_sources: int
    total_chars: int


def format_context(search_results: list) -> FormattedContext:
    """
    Format search results into a numbered context block.

    Transforms raw SearchResult objects into a structured text block
    that the LLM can easily parse and cite.

    Example output:
        [Source 1] NVIDIA, 2024 Annual Report (Relevance: 0.72)
        Revenue for fiscal year 2024 reached $60.9 billion,
        representing a 126% increase year over year...

        [Source 2] NVIDIA, 2023 Annual Report (Relevance: 0.65)
        The company reported revenue of $26.9 billion...
    """
    if not search_results:
        return FormattedContext(
            text="No relevant documents found.",
            num_sources=0,
            total_chars=0,
        )

    context_parts = []

    for i, result in enumerate(search_results, 1):
        # Format: [Source N] Company, Year Report (Relevance: score)
        source_header = (
            f"[Source {i}] {result.company.upper()}, "
            f"{result.year} Annual Report "
            f"(Relevance: {result.score:.2f})"
        )

        context_parts.append(f"{source_header}\n{result.text}")

    context_text = "\n\n".join(context_parts)

    return FormattedContext(
        text=context_text,
        num_sources=len(search_results),
        total_chars=len(context_text),
    )


# ──────────────────────────────────────────────
# 🔨 PROMPT ASSEMBLY
# ──────────────────────────────────────────────

def build_rag_prompt(
    query: str,
    search_results: list,
    include_tables: bool = False,
    table_context: str = "",
) -> tuple[str, str]:
    """
    Build the complete RAG prompt.

    WHY TWO RETURNS?
    Returns (system_prompt, user_prompt) separately because
    some LLM APIs handle system prompts differently:
    - Gemini: prepended to the prompt
    - OpenAI: separate "system" message role
    - Local models: may use special tokens

    Args:
        query: The user's question
        search_results: List of SearchResult objects from search()
        include_tables: Whether to include table context
        table_context: Markdown tables relevant to the query

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # Format the context
    context = format_context(search_results)

    # Build the user prompt
    prompt_parts = [
        "CONTEXT FROM FINANCIAL DOCUMENTS:",
        "=" * 40,
        context.text,
        "=" * 40,
    ]

    # Add table context if available
    if include_tables and table_context:
        prompt_parts.extend([
            "",
            "RELEVANT FINANCIAL TABLES:",
            "=" * 40,
            table_context,
            "=" * 40,
        ])

    prompt_parts.extend([
        "",
        f"QUESTION: {query}",
        "",
        f"Please answer based on the {context.num_sources} source(s) above. "
        "Cite your sources using [Source N] notation.",
    ])

    user_prompt = "\n".join(prompt_parts)

    logger.info(
        f"📝 Prompt built: {context.num_sources} sources, "
        f"{context.total_chars:,} context chars"
    )

    return SYSTEM_PROMPT, user_prompt


# ──────────────────────────────────────────────
# 🧪 TEST: Preview a prompt
# ──────────────────────────────────────────────
if __name__ == "__main__":
    from backend.engines.search import search

    print("\n" + "=" * 60)
    print("🧪 PROMPT BUILDER TEST")
    print("=" * 60)

    query = "What was NVIDIA's total revenue in fiscal year 2024?"
    results = search(query, top_k=3, company="nvidia")

    system_prompt, user_prompt = build_rag_prompt(query, results)

    print(f"\n--- SYSTEM PROMPT ---\n{system_prompt}")
    print(f"\n--- USER PROMPT ---\n{user_prompt[:1000]}...")
    print(f"\n--- STATS ---")
    print(f"System prompt: {len(system_prompt)} chars")
    print(f"User prompt:   {len(user_prompt)} chars")
    print(f"Total:         {len(system_prompt) + len(user_prompt)} chars")

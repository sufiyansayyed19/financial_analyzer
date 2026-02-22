# 📓 Phase 3 Learning Journal — RAG Pipeline

**Date:** February 22, 2026
**Duration:** ~1 hour
**Result:** ✅ Full RAG pipeline working — questions answered with citations in 6.4s

---

## 🗂️ Files Created

| # | File | Purpose |
|---|------|---------|
| 1 | `backend/llm/llm_client.py` | LLM abstraction (Gemini implementation) |
| 2 | `backend/llm/prompt_builder.py` | RAG prompt templates + citation formatting |
| 3 | `backend/services/rag_pipeline.py` | Orchestrator: search → prompt → LLM → answer |
| 4 | `backend/core/config.py` (updated) | Added LLM settings (model, temperature, API key) |

---

## 🧠 Key Concepts Learned

### 1. What Is RAG (Retrieval-Augmented Generation)?

**The Problem:**
- LLMs like Gemini/GPT have a knowledge cutoff date — they don't know YOUR documents
- If you ask "What was NVIDIA's 2024 revenue?", the LLM might hallucinate or say outdated info

**The Solution (RAG):**
```
User question
    │
    ▼ RETRIEVE: Search your database for relevant chunks
    │
    ▼ AUGMENT: Inject those chunks into the prompt as context
    │
    ▼ GENERATE: LLM reads the context and generates a grounded answer
```

**Key insight:** RAG doesn't make the LLM smarter — it gives the LLM the RIGHT INFORMATION to work with. The LLM is just a "reader" of your data.

### 2. The Strategy Pattern (Design Pattern)

**What:** Define an interface, then multiple implementations can be swapped.

```python
# Interface (what must be implemented)
class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

# Implementation 1: Gemini
class GeminiClient(BaseLLMClient):
    def generate(self, prompt): ...  # calls Gemini API

# Implementation 2 (future): OpenAI
class OpenAIClient(BaseLLMClient):
    def generate(self, prompt): ...  # calls OpenAI API
```

**Why it matters:** The entire RAG pipeline just calls `client.generate()`. Switching from Gemini to OpenAI = changing ONE config variable. No code changes.

**Interview answer:** "I used the Strategy pattern for LLM integration — a base class defines the interface, and each provider implements it. Switching from Gemini to OpenAI is a one-line config change."

### 3. Prompt Engineering for RAG

**Bad prompt:**
```
Here's some text. What was the revenue?
```

**Good prompt (what we built):**
```
SYSTEM: You are FinRAG, a financial analyst. Answer ONLY from
provided context. Use [Source N] citations. Say "I don't have
sufficient information" when data is missing.

CONTEXT:
[Source 1] NVIDIA, 2024 Annual Report (Relevance: 0.70)
Revenue for fiscal year 2024 reached $60.9 billion...

[Source 2] NVIDIA, 2024 Annual Report (Relevance: 0.69)
Data Center revenue was $47.5 billion...

QUESTION: What was NVIDIA's revenue in 2024?
Please cite your sources using [Source N] notation.
```

**Key design decisions:**
1. **System prompt** = the LLM's "job description" (financial analyst, cite sources)
2. **Numbered sources** = enables `[Source 1]` citation format
3. **Include relevance score** = helps LLM prioritize higher-relevance sources
4. **"Say I don't know"** = prevents hallucination when context is insufficient

### 4. System Prompt vs User Prompt

**System prompt:** WHO the LLM is and HOW it should behave
- "You are a financial analyst"  
- "Only use provided context"
- "Cite sources with [Source N]"

**User prompt:** WHAT to answer
- The context (retrieved chunks)
- The question

**Why separate?** Different LLM APIs handle them differently:
- Gemini: Prepended together
- OpenAI: Separate `role: "system"` message
- Some local models: Special `<|system|>` tokens

Our `build_rag_prompt()` returns both separately → provider-agnostic.

### 5. Temperature Setting

**What:** Controls randomness in LLM output.

| Temperature | Behavior | Use Case |
|-------------|----------|----------|
| `0.0` | Deterministic, same answer every time | Factual Q&A, code |
| `0.1` | Almost deterministic, tiny variation | **What we use** |
| `0.7` | Creative, varied answers | Creative writing |
| `1.0` | Very random | Brainstorming |

**Why 0.1 for financial RAG:** We want consistent, factual answers. Creativity = hallucination risk when answering "What was the revenue?"

### 6. The Lazy Singleton Pattern (Repeated)

We used this pattern AGAIN for the LLM client:
```python
_client = None

def get_llm_client():
    global _client
    if _client is None:
        _client = GeminiClient()  # Created once on first use
    return _client
```

**Where we've used it so far:**
1. `config.py` → Settings object
2. `embedder.py` → Embedding model
3. `llm_client.py` → LLM client

**Why keep repeating it:** Expensive resources (models, API clients) should be loaded ONCE and reused. This is the standard pattern.

### 7. Retry with Exponential Backoff

**What:** When an API rate-limits you (HTTP 429), wait and retry.

```python
for attempt in range(3):
    try:
        response = api_call()
        return response
    except RateLimitError:
        wait = 5 * (attempt + 1)  # 5s, 10s, 15s
        time.sleep(wait)
```

**Why exponential:** Each retry waits LONGER, giving the rate limit more time to reset. This is a standard pattern for any API integration.

### 8. Service Layer Architecture

```
rag_pipeline.py (SERVICE layer — orchestration)
    ├── search.py (retrieval — Phase 2)
    ├── prompt_builder.py (prompt assembly)
    └── llm_client.py (generation)
```

**Why a separate service layer:** Each component is testable and replaceable independently:
- Swap search algorithm? Only touch `search.py`
- Change LLM? Only touch `llm_client.py`
- Modify prompt? Only touch `prompt_builder.py`
- The orchestrator (`rag_pipeline.py`) just connects them

### 9. Structured Response Objects

```python
@dataclass
class RAGResponse:
    answer: str           # The LLM's answer
    query: str            # Original question
    sources: list[dict]   # Source citations
    retrieval_time: float # Search time
    generation_time: float # LLM time
    total_time: float     # End-to-end time
```

**Why not just return a string?** Because the API/frontend needs:
- The answer (display to user)
- Sources (show citation cards)
- Timing (performance monitoring)

Structured responses make the API layer (Phase 5) trivial to build.

---

## ⚡ Challenges Faced & Solutions

### Challenge #1: Gemini Rate Limiting (429)
**What happened:** Rapid-fire testing hit the free tier per-minute limit.
**Fix:** Added retry logic with exponential backoff (5s, 10s, 15s delays).
**Lesson:** Always build retry logic for external APIs — they WILL fail.

### Challenge #2: Model Name Selection
**What happened:** `gemini-2.0-flash` was hitting rate limits consistently.
**Fix:** Switched to `gemini-2.5-flash` (newer, higher free-tier limits).
**Lesson:** API free tiers change — always have a fallback model.

### Challenge #3: Deprecated SDK Warning
**What happened:** `google.generativeai` package shows FutureWarning about switching to `google.genai`.
**Status:** Not urgent — current package works. Migration planned for later.

---

## 📊 Performance Results

| Metric | Value |
|--------|-------|
| Total query time | **6.37 seconds** |
| Retrieval time | 4.09s (includes first model load) |
| LLM generation time | 2.27s |
| Sources retrieved | 5 |
| Top relevance score | 0.700 |
| Answer quality | ✅ Correct, cited, segment breakdown |

**Note:** First query is slow (4s) because the embedding model loads. Subsequent queries are ~1-2s retrieval.

---

## 🎯 Example RAG Output

```
❓ What was NVIDIA revenue in 2024?

🤖 Answer:
NVIDIA's total revenue for fiscal year 2024 was $60.9 billion [Source 1].
This represents a significant increase of 126% compared to the previous
year [Source 1].

The company's platforms address four main markets:
- Data Center: $47.5 billion
- Gaming: $10.4 billion  
- Professional Visualization: $1.6 billion
- Automotive: $1.1 billion [Source 3]

📚 Sources:
[1] NVIDIA 2024 (relevance: 0.700)
[2] NVIDIA 2024 (relevance: 0.695)
[3] NVIDIA 2024 (relevance: 0.683)
```

---

## 💡 Interview Talking Points

> "For Phase 3, I built the full RAG pipeline connecting semantic search to Google Gemini. The architecture uses the Strategy pattern for LLM integration — there's an abstract base class, and each provider just implements `generate()`. Switching from Gemini to OpenAI is a one-line config change.
>
> The prompt engineering was critical. I built a financial domain system prompt that instructs the LLM to only use provided context, cite sources with [Source N] notation, and admit when data is insufficient. Temperature is set to 0.1 for deterministic, factual answers.
>
> End-to-end, a query takes ~6 seconds: 2s for search, 2s for Gemini. The answer correctly returned NVIDIA's $60.9B revenue with a segment breakdown, all properly cited from the actual annual report."

---

## 📁 Updated Project Structure

```
backend/
├── llm/                          ← NEW DIRECTORY IN USE
│   ├── __init__.py
│   ├── llm_client.py            ← NEW: Gemini client + Strategy pattern
│   └── prompt_builder.py        ← NEW: RAG prompt templates
├── services/                     ← NEW DIRECTORY IN USE
│   ├── __init__.py
│   └── rag_pipeline.py          ← NEW: RAG orchestrator
├── engines/
│   ├── embedder.py              (Phase 2)
│   └── search.py                (Phase 2)
└── core/
    └── config.py                ← UPDATED: LLM settings
```

---

## ➡️ What's Next: Phase 4 or Phase 5

The core RAG system (Phases 1-3) is **complete**. Two paths forward:
- **Phase 4 (Analytics):** Add sentiment analysis, risk classification, theme extraction
- **Phase 5 (FastAPI):** Add REST API endpoints → enables the upload/search UI

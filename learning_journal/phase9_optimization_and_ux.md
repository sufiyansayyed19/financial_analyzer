# 🚀 Phase 9: Advanced Optimization, UX & Polish
**Goal:** Take our MVP RAG system from "functional" to a "production-ready" chat experience. We added Hybrid Search for better retrieval, In-Memory Caching for speed/cost, Server-Sent Events (SSE) for real-time text streaming, conversational memory for follow-up questions, and polished CSS animations.

---

## 🏗️ 1. Hybrid Search (Vector + BM25)
**The Problem:** Vector search (Cosine Similarity) is great for "semantic" meaning, but it struggles with exact keyword matching (like catching an explicit mention of "10-K" or specific part numbers).

**The Solution:** Hybrid search combines two mechanisms and re-ranks the results:
1.  **Dense Retrieval (Vector Search):** We kept our `all-MiniLM-L6-v2` embeddings. Finds paragraphs *conceptually* related to the query.
2.  **Sparse Retrieval (BM25):** We added `rank_bm25` (Okapi BM25). This is a token-based algorithm that excels at exact keyword matching.
3.  **Reciprocal Rank Fusion (RRF):** This algorithm combines the results. It looks at the *rank* (position) of a document in both lists and assigns a combined score: `RRF_Score = 1 / (k + Vector_Rank) + 1 / (k + BM25_Rank)`.

**Why it matters:** It gives us the best of both worlds. If a user asks *"What was the exact EPS for TCS?"*, BM25 catches "EPS", while Vector Search catches the financial context.

---

## 🚦 2. Smart Company Detection & Diversified Retrieval
**The Problem:** 
- If a user asked *"Compare revenue targets"*, vector search might pull 5 paragraphs all from *one* company (e.g. NVIDIA) if that doc was just highly matched, completely missing the "comparison" aspect.
- Conversely, if a user asked *"revenue of tcs"*, the system might distribute retrieved chunks across 8 different companies if no filter was explicitly set.

**The Solution:**
1.  **Auto-detection:** We built logic to scan the user's query lowercase string against known companies in the database (`f" {company} " in query_lower`). If detected, we automatically set `company="tcs"`.
2.  **Diversified Round-Robin:** If NO company filter is set (a true cross-company query), we temporarily boost `top_k` up to 10+. Then, we group the raw retrieved chunks by company and select them "Round Robin" (one from A, one from B, one from C...) until we hit our target. 

**Why it matters:** This ensures cross-company questions actually get data from multiple companies, while explicit questions don't get diluted by irrelevant companies.

---

## ⚡ 3. In-Memory Answer Caching
**The Problem:** Calling the LLM API (Gemini) takes 3-8 seconds and costs quota/money. If 5 users ask *"What is the dashboard status?"*, we shouldn't ask the LLM 5 times.

**The Solution:** We implemented an in-memory dictionary cache in `backend/engines/cache.py`.
- **The Key:** A SHA-256 hash of the normalized query + filters (e.g., `hash("what is revenue?|tcs|None|None")`).
- **The Cache Entry:** Stores the generated answer, the source chunks, and timestamp.
- **Eviction / TTL:** The cache holds a max of 500 entries (LRU-style eviction) and entries expire after 1 hour (TTL).
- **Invalidation:** *Crucially*, when a user adds or deletes a PDF (`/api/documents`), we `cache.invalidate()` to wipe the cache. Stale data is a huge risk in financial tasks.

**Why it matters:** 0.001s response times for repeated queries, 0 API cost.

---

## 📡 4. Streaming Responses (SSE)
**The Problem:** Waiting 8 seconds staring at a spinner is terrible UX. Users think the app is broken.

**The Solution:** Server-Sent Events (SSE). 
- **Backend (`yield`):** We switched from `generate_content` to `generate_content_stream()`. The endpoint now uses FastAPIs `StreamingResponse`, yielding partial text chunks (tokens) as they arrive.
- **Frontend (`TextDecoder`):** We ditched `await response.json()`. Instead, we use `response.body.getReader()`, decode the byte stream, and apply incoming tokens directly to React state (`setStreamingText(prev => prev + token)`).

**Why it matters:** The perceived latency drops to < 1 second. The user starts reading *immediately*, matching the UX of ChatGPT.

---

## 💬 5. Chat History (Conversational Memory)
**The Problem:** RAG models have "goldfish memory." Each API call is totally isolated. You can't ask *"What about their risks?"* after asking about revenue, because the LLM doesn't know who "their" is.

**The Solution:**
1.  **React State:** Frontend maintains a `messages` array holding the history of the current conversation session.
2.  **API Payload:** We changed `AskRequest` to `ChatRequest`, accepting a `history: list[ChatMessage]` field.
3.  **Prompt Injection:** In the backend `ask_stream()` endpoint, we grab the last 6 messages (3 conversational turns), format them as a transcript (`User: ... \n Assistant: ...`), and inject them *before* the new question in the context window.

**Why it matters:** This transforms a simple "search bar" into a natural dialogue agent.

---

## 🎨 6. UI Polish (CSS & UX)
**The Problem:** The app looked basic. Text snapped into existence, and loading states were jarring.

**The Solution:**
- **Markdown Rendering:** Installed `react-markdown` so the LLM output renders nicely with bolding, lists, code blocks, and tables using specific CSS prose classes.
- **Skeleton Shimmers:** Replaced the loading spinner with CSS `background-position` animations that look like shimmering "placeholder" cards (Skeleton loaders) to match the layout of the incoming data.
- **CSS Keyframes:** Added `@keyframes fadeInUp` to stagger the entrance of cards, giving the app a fluid, modern feel.

**Why it matters:** The app now feels premium, responsive, and trustworthy.

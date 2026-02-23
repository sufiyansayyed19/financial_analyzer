# 🧠 FinRAG: Comprehensive Theory & Concepts Guide

This document organizes all theoretical concepts, design patterns, and technologies used (or related) in the FinRAG project. Use this for structured interview revision.

---

## 1. System Architecture & Design Patterns

### 1.1 Object-Oriented Design Patterns
*   **Singleton Pattern**
    *   *Usage in FinRAG:* `settings` (config), `get_llm_client()` (Gemini API), `Embedder()` (SentenceTransformers).
    *   *Theory:* Ensures a class has only one instance and provides a global point of access to it. Prevents redundant API connections or re-loading heavy machine learning models into memory multiple times.
*   **Strategy Pattern**
    *   *Usage in FinRAG:* `BaseLLMClient` (Interface) -> `GeminiClient` (Concrete Implementation).
    *   *Theory:* Defines a family of algorithms, encapsulates each one, and makes them interchangeable. Allows switching from Gemini to OpenAI without rewriting the core RAG pipeline.
*   **Factory Pattern** (Related, not explicitly used)
    *   *Theory:* Creating objects without specifying the exact class to create. Could be used to dynamically instantiate either a `GeminiClient` or `OpenAIClient` based on `.env` variables.

### 1.2 Web & API Architecture
*   **REST API Principles**
    *   *Usage in FinRAG:* `GET /api/documents`, `POST /api/upload`, `DELETE /api/documents/{id}`.
    *   *Theory:* Stateless, client-server communication using standard HTTP methods (GET, POST, PUT, DELETE) to manipulate resources.
*   **Server-Sent Events (SSE)**
    *   *Usage in FinRAG:* Streaming the LLM response word-by-word (`/api/ask/stream`).
    *   *Theory:* A unidirectional protocol where the client opens a connection and the server pushes data updates continuously over HTTP. Simpler than WebSockets when two-way communication isn't needed.
*   **Asynchronous I/O (async/await)**
    *   *Usage in FinRAG:* FastAPI endpoints (`async def`).
    *   *Theory:* Non-blocking execution. While waiting for a slow network request (like querying Gemini), the event loop pauses the current function and handles other incoming requests, vastly increasing server throughput.
*   **Idempotency**
    *   *Usage in FinRAG:* The data pipeline skips PDFs that are already processed.
    *   *Theory:* An operation that produces the same result regardless of how many times it is executed. Critical for robust data pipelines to prevent duplicate entries on failure/retries.

---

## 2. Natural Language Processing (NLP) & RAG

### 2.1 Retrieval-Augmented Generation (RAG)
*   **The RAG Concept**
    *   *Usage in FinRAG:* The core project architecture.
    *   *Theory:* Combining a retrieval system (database search) with a generative model (LLM). Solves LLM hallucinations and knowledge cutoff limitations by injecting private/recent data directly into the prompt context.
*   **Chunking Strategies**
    *   *Usage in FinRAG:* Sliding Window Chunking (1000 chars, 200 overlap).
    *   *Theory:* Splitting large documents into smaller pieces. Overlap preserves context at boundaries. Advanced variations: Semantic chunking (splitting by topic changes) or recursive character splitting.
*   **Prompt Engineering & Grounding**
    *   *Usage in FinRAG:* Instructing Gemini to *only* use provided context and format answers with `[Source N]` tags.
    *   *Theory:* Designing the input instructions (System Prompt vs. User Prompt) to constrain the LLM's behavior, reduce hallucination, and enforce citation formatting.

### 2.2 Semantic Understanding & Embeddings
*   **Dense Vectors (Embeddings)**
    *   *Usage in FinRAG:* `all-MiniLM-L6-v2` generating 384-dimensional arrays.
    *   *Theory:* Representing words or sentences as continuous vectors in a multidimensional mathematical space. Concepts with similar meanings are located physically close to each other in this space.
*   **Cosine Similarity**
    *   *Usage in FinRAG:* Comparing the user's query vector against stored document chunk vectors.
    *   *Theory:* A mathematical metric calculating the cosine of the angle between two vectors. `1.0` means identical direction (meaning), `0.0` is orthogonal (unrelated), `-1.0` is opposite. Fast to compute via dot-product if vectors are normalized.

### 2.3 Classical Information Retrieval (IR)
*   **BM25 (Sparse Retrieval)**
    *   *Usage in FinRAG:* The keyword-matching half of the Hybrid Search engine.
    *   *Theory:* A statistical ranking function (TF-IDF based). It scores documents based on how frequently the exact search terms appear, penalizing words that are too common across the whole database (like "the" or "company").
*   **TF-IDF vs BM25** (Related theory)
    *   *Theory:* TF-IDF (Term Frequency-Inverse Document Frequency) is the simpler predecessor. BM25 improves upon it by adding "term frequency saturation" (mentioning a word 100 times isn't 10x better than mentioning it 10 times) and document length normalization (a match in a short document is worth more than a match in a huge document).

### 2.4 Search Optimization
*   **Hybrid Search**
    *   *Usage in FinRAG:* Combining Dense (Vector) and Sparse (BM25) retrieval.
    *   *Theory:* Solving the "vocabulary mismatch problem." Vectors catch semantic meaning ("income" matches "revenue"), but fail on exact keywords (e.g., specific acronyms like "ESG" or part numbers). BM25 handles keywords.
*   **Reciprocal Rank Fusion (RRF)**
    *   *Usage in FinRAG:* Blending the scores from Vector Search and BM25.
    *   *Theory:* An algorithm that combines multiple ranked lists. It rewards documents that appear near the top of *multiple* independent lists using the formula: `Score = 1 / (k + rank_1) + 1 / (k + rank_2)`.
*   **Diversified Retrieval (Round Robin)**
    *   *Usage in FinRAG:* Ensuring cross-company queries retrieve chunks from multiple companies.
    *   *Theory:* Preventing result dominated by a single highly-matched document. Ensures variety in the final context window for comparison-based questions.

---

## 3. Data Engineering & Backend

### 3.1 Text Processing
*   **Regular Expressions (Regex)**
    *   *Usage in FinRAG:* Removing page numbers, headers, invisible characters, and excessive whitespace.
    *   *Theory:* A sequence of characters specifying a search pattern. Extremely powerful but computationally expensive if written poorly (Catastrophic Backtracking).
*   **Text Normalization & Unicode**
    *   *Usage in FinRAG:* Resolving typographic ligatures (`ﬁ` -> `fi`) and control characters.
    *   *Theory:* Standardizing text encodings before NLP processing so that equivalent strings (like 'cafe' and 'café', or varying hyphen types) are mathematically identical to the computer.

### 3.2 Database & Storage
*   **Object-Relational Mapping (ORM)**
    *   *Usage in FinRAG:* SQLAlchemy defining `Document` and `Chunk` models.
    *   *Theory:* A technique to map database tables to object-oriented classes. It abstracts away raw SQL, provides type safety, and allows switching database engines (SQLite to PostgreSQL) with minimal code changes.
*   **Normalization vs. Denormalization**
    *   *Usage in FinRAG:* We explicitly *denormalized* `company` and `year` onto the `chunks` table.
    *   *Theory:* Normalization (splitting data into multiple tables to reduce redundancy) saves space but requires expensive `JOIN` operations. Denormalization (copying data into the main table) increases storage size but drastically speeds up read/search queries. Crucial trade-off in database design.
*   **Write-Ahead Logging (WAL)**
    *   *Usage in FinRAG:* Configured in SQLite to allow concurrent reads/writes.
    *   *Theory:* A database mechanism where modifications are written to a log *before* being applied to the main database file. Ensures data integrity during crashes and improves concurrency.
*   **In-Memory Caching (TTL/LRU)**
    *   *Usage in FinRAG:* Caching LLM responses in Python dictionaries.
    *   *Theory:* Storing expensive, frequently accessed data in RAM for instant retrieval. **TTL (Time-To-Live)** dictates how long data stays fresh (e.g., 1 hour). **LRU (Least Recently Used)** dictates which old data gets deleted when the cache is full (e.g., max 500 entries).

---

## 4. Frontend & User Experience (UX)

### 4.1 React Concepts
*   **Single Page Application (SPA)**
    *   *Usage in FinRAG:* The entire frontend built with React and Vite.
    *   *Theory:* A web app that interacts with the user by dynamically rewriting the current web page with new data from the server, rather than loading entire new HTML pages. Feels faster and more responsive like a native app.
*   **State Management**
    *   *Usage in FinRAG:* `useState` for query input, chat messages, and streaming text.
    *   *Theory:* The data structure that dictates what the UI currently renders. When state changes (e.g., a new token arrives from SSE), React automatically re-renders just that specific part of the screen.
*   **Hooks (`useEffect`, `useRef`)**
    *   *Usage in FinRAG:* `useEffect` to fetch available companies on load; `useRef` to auto-scroll chat to the bottom.
    *   *Theory:* Functions that let you "hook into" React state and lifecycle features (like mounting, unmounting, or focusing DOM elements directly).

### 4.2 UI Design Patterns
*   **Skeleton Loaders**
    *   *Usage in FinRAG:* The shimmering placeholders that appear while waiting for search results.
    *   *Theory:* A UX pattern used to indicate a loading state by displaying a blank version of the component. It reduces perceived waiting time and prevents layout shifts (CLS - Cumulative Layout Shift).
*   **Glassmorphism**
    *   *Usage in FinRAG:* Tailwind CSS styling for cards and nav bars (`backdrop-blur`, semi-transparent backgrounds).
    *   *Theory:* A UI trend emphasizing semi-transparent, frosted-glass-like backgrounds, layered depth, and soft borders. Popularized by modern OS interfaces (macOS, Windows 11).

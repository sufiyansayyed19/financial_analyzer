# 🎯 FinRAG: 100+ Senior Interview Questions & Answers

This guide contains 105 interview questions ranging from basic to advanced, specifically tailored for a Senior Full-Stack/AI Engineer who built an end-to-end RAG system like FinRAG.

It covers Architecture, NLP/RAG, Data Engineering, Backend, Frontend, and "Why X over Y" behavioral/technical decisions.

---

## Part 1: Architecture & "Why This Over That" (System Design)

1.  **Q: Why did you choose FastAPI over Django or Flask for this project?**
    *   **A:** Django is a heavy, "batteries-included" monolith suited for tightly coupled full-stack apps (HTML templates + DB). Flask is lightweight but synchronous by default. FastAPI provides native `async/await` support (crucial for waiting on slow LLM API calls without blocking the server), automatic Pydantic data validation, and auto-generated Swagger documentation, making it the modern standard for AI microservices.
2.  **Q: Why use SQLite instead of PostgreSQL or MongoDB?**
    *   **A:** For the MVP and local development, SQLite requires zero infrastructure setup while still being a robust SQL database. Because I used SQLAlchemy (an ORM), the python code is database-agnostic. To scale to PostgreSQL in production, I only need to change the `DATABASE_URL` connection string. I chose SQL over MongoDB because the relationship between Documents and Chunks is strictly relational (1-to-Many).
3.  **Q: Why did you build your own Vector Search using Cosine Similarity instead of using Pinecone or ChromaDB?**
    *   **A:** To deeply understand the math and mechanics under the hood. For a dataset of ~25,000 chunks, a simple numpy dot-product (cosine similarity on normalized vectors) executes in <100ms in RAM. Adding Pinecone introduces network latency, cost, and a third-party dependency that wasn't strictly necessary for this scale. (Though I would migrate to pgvector or Pinecone at millions of rows).
4.  **Q: Why did you choose React over vanilla HTML/JS or a server-rendered approach (like Jinja)?**
    *   **A:** A chat interface requires complex state management (streaming text, chat history arrays, real-time UI updates). React's component-based architecture and Virtual DOM are perfectly suited for building dynamic, reactive single-page applications (SPAs) compared to traditional server-rendered templates.
5.  **Q: Explain your decision to denormalize the `company` and `year` fields into the `chunks` table.**
    *   **A:** In a normalized database, `chunks` would only have a `document_id`. To filter a search by "TCS 2024", the system would have to perform an expensive `JOIN` between the millions of chunks and the documents table for every single query. By denormalizing (copying) `company` and `year` into the `chunks` table, filters become simple, lightning-fast indexed WHERE clauses, trading a tiny bit of storage space for massive read-speed gains.
6.  **Q: Why use Server-Sent Events (SSE) instead of WebSockets for streaming the LLM response?**
    *   **A:** WebSockets are bi-directional (chat rooms, multiplayer games). For an LLM response, the communication is strictly unidirectional (Server -> Client). SSE is a simpler standard built on top of standard HTTP, handles reconnections automatically, and is perfectly suited for streaming text tokens.
7.  **Q: Why did you extract tables into `.md` format specifically for the LLM?**
    *   **A:** LLMs are trained heavily on Markdown. If you pass a table as raw JSON, it consumes significantly more tokens (curly braces, quotes) and the LLM has to "parse" it. A Markdown pipe-table `| Revenue | $50 |` is natively understood by the LLM, highly token-efficient, and easy to inject into the text prompt.
8.  **Q: How did you design the backend to ensure the API doesn't freeze when Gemini takes 8 seconds to respond?**
    *   **A:** I defined the FastAPI endpoint using `async def`. Under the hood, this uses Python's `asyncio` event loop. When the code hits `await client.generate()`, the server "yields" control back to the event loop, allowing it to process other users' HTTP requests until the Gemini network response arrives.
9.  **Q: If I wanted to scale this to 10,000 users tomorrow, what are the first three architectural changes you would make?**
    *   **A:** 1) Migrate from SQLite to a managed PostgreSQL instance with `pgvector` for scalable vector search. 2) Move the PDF ingestion pipeline to background worker queues (like Celery + Redis) so uploads don't block the API. 3) Replace the in-memory Python dictionary cache with Redis for distributed caching across multiple API server instances.
10. **Q: Why did you use Reciprocal Rank Fusion (RRF) instead of just averaging the scores of Vector and BM25?**
    *   **A:** BM25 scores are unbounded (often 10 to 50+), while Cosine Similarity is strictly bounded between -1 and 1. You cannot average them mathematically. RRF ignores the absolute scores and instead looks at the *positional rank* (1st, 2nd, 3rd) in both lists, providing a mathematically sound way to blend totally different scoring algorithms.

---

## Part 2: RAG & NLP Mastery

### Basic RAG
11. **Q: What problem does Retrieval-Augmented Generation (RAG) solve?**
    *   **A:** It solves LLM knowledge cutoffs and hallucinations by dynamically retrieving private or up-to-date data from a database and injecting it into the prompt exactly when the user asks a question.
12. **Q: Explain the difference between Dense Retrieval and Sparse Retrieval.**
    *   **A:** Dense retrieval uses AI-generated vectors (embeddings) to capture the *semantic meaning* of text (e.g., matching "income" with "revenue"). Sparse retrieval (like BM25) uses frequency-based algorithms to find *exact keyword matches* (e.g., matching "ESG-402").
13. **Q: What is the purpose of Semantic Search?**
    *   **A:** To find relevant information based on the intent and context of the search query, rather than relying strictly on exact word matches.
14. **Q: What does a SentenceTransformer do?**
    *   **A:** It's an NLP model that takes a sentence or paragraph and maps it to a high-dimensional vector space (an array of floats) where similar sentences are positioned close to each other.
15. **Q: Why did you choose an overlap of 200 characters in your chunking strategy?**
    *   **A:** Without overlap, a hard cut might split a crucial sentence in half (e.g., "[NVIDIA's revenue was] | [$60 billion]"). Overlapping ensures that boundary context is preserved in at least one of the chunks.
16. **Q: What is a System Prompt vs a User Prompt?**
    *   **A:** The System Prompt defines the LLM's persona, rules, and constraints ("You are a financial analyst. Only answer from context"). The User Prompt contains the specific task, the retrieved context data, and the actual question asked by the user.

### Intermediate RAG
17. **Q: Explain how Cosine Similarity works mathematically.**
    *   **A:** It computes the cosine of the angle between two vectors: `(A · B) / (||A|| * ||B||)`. If the vectors are normalized (magnitude of 1), the denominators equal 1, meaning Cosine Similarity simplifies to just the dot product `A · B`.
18. **Q: How does BM25 improve upon raw TF-IDF?**
    *   **A:** BM25 introduces term frequency saturation (mentioning "revenue" 100 times isn't 10x better than 10 times) and document length normalization (finding the word "revenue" in a 1-page document is a stronger signal than finding it in a 100-page document).
19. **Q: What is the "Vocabulary Mismatch Problem" and how did you solve it?**
    *   **A:** It's when the user searches for a specific acronym (like "10-K") but the vector embedding focuses on the semantic concept of "filing" and misses the exact keyword. I solved it using Hybrid Search (combining Vector Search's semantic understanding with BM25's exact keyword matching).
20. **Q: Why is chunk size a critical hyperparameter in RAG?**
    *   **A:** If chunks are too small (e.g., 50 chars), they lack the context needed for the LLM to understand them. If chunks are too large (e.g., 5000 chars), they dilute the signal, make retrieval less precise, and eat up the LLM's context window limit.
21. **Q: How did you enforce strict citations to prevent hallucinations?**
    *   **A:** I explicitly injected formatted sources into the prompt (e.g., `[Source 1] Text...`) and instructed the LLM in the System Prompt to append `[Source N]` after every claim. I also instructed it to explicitly state "I don't know" if the answer wasn't in the provided text.
22. **Q: How did you solve the cross-company query problem (e.g., "Compare revenues")?**
    *   **A:** I implemented a diversified "Round Robin" retrieval strategy. Rather than taking the top 5 raw vectors (which might all belong to NVIDIA), the system temporarily retrieves the top 15, groups them by company, and picks one from each company repeatedly until it hits 5, guaranteeing a varied context window.
23. **Q: How did you handle conversational memory in a stateless RAG pipeline?**
    *   **A:** The React frontend maintains a `history` array of the last few messages. When a user asks a follow-up, the frontend sends this history. The backend formats it as a dialogue transcript and prepends it to the prompt so the LLM has context for pronouns like "What about *their* risks?".

### Advanced RAG & Models
24. **Q: Why did you set the LLM Temperature to 0.1?**
    *   **A:** Temperature controls output randomness. In a financial application, we want highly deterministic, factual answers based *only* on the text. A high temperature (0.8) encourages creative variation, which leads directly to hallucinations.
25. **Q: What is the dimension of `all-MiniLM-L6-v2` and why does dimensionality matter?**
    *   **A:** It outputs 384 dimensions. Higher dimensions (like OpenAI's 1536) can capture more nuanced semantic relationships but require 4x the storage space and 4x the computational power to search. 384 is the sweet spot for balance between speed, cost, and accuracy for a local project.
26. **Q: If a user asks a question totally unrelated to finance (e.g., "What is the capital of France?"), how does your system handle it?**
    *   **A:** The retrieved chunks will have very low relevance scores. Because the System Prompt demands the LLM *only* answer using the provided context, the LLM will correctly output: "I don't have sufficient information in the provided documents to answer that."
27. **Q: How would you implement "Re-ranking" (like Cohere Rerank) in this pipeline if you needed even higher accuracy?**
    *   **A:** I would do a fast initial retrieval of the Top 50 chunks using my local Cosine Similarity. Then, I would pass those 50 chunks + the user query to a Cross-Encoder (Reranker) model. The Cross-Encoder processes the query and the chunk *together* through the Transformer attention layers, producing a highly accurate, but computationally expensive, final Top 5 ranking.
28. **Q: Explain the exact workflow of your Smart Company Auto-Detection.**
    *   **A:** Before passing the query to the search engine, the backend retrieves a list of all distinct `.company` names from the DB. It does a fast substring matching check (with word boundaries) against the lowercase user query. If "tcs" is found, it automatically applies `company="tcs"` as a hard SQL filter to the retrieval step, entirely bypassing the need for the LLM to figure out the target company.

---

## Part 3: Data Engineering & Text Processing

### Basic Data Engineering
29. **Q: Why is raw PDF extraction text essentially garbage?**
    *   **A:** PDFs are visual formats mapping characters to X/Y coordinates on a page. They have no concept of "paragraphs". Extractors grab page numbers, repeating headers, non-breaking spaces, and split hyphenated words across lines, requiring heavy cleaning.
30. **Q: What library did you use for PDF extraction and why?**
    *   **A:** PyMuPDF (`fitz`). It is C-based, extremely fast, and supports both raw text extraction and structured bounding-box layout analysis (which enabled the `find_tables()` feature) from a single dependency.
31. **Q: What is an idempotent pipeline?**
    *   **A:** A pipeline that can be run multiple times safely. In FinRAG, the ingestion script checks the DB if `file_name` already exists. If yes, it skips. This prevents database duplication if the script crashes halfway and is restarted.

### Intermediate Data Engineering
32. **Q: How did you fix broken hyphenated words ("com-\npany")?**
    *   **A:** Using a targeted regular expression: `r"(\w)-\s*\n\s*(\w)"` and replacing it with `r"\1\2"`. It looks for a word character, a hyphen, a newline (and any surrounding whitespace), and another word character, stitching them back together.
33. **Q: What are typographic ligatures and why are they dangerous for NLP?**
    *   **A:** Specialized PDF fonts combine letters like "f" and "i" into a single unicode character "ﬁ" (U+FB01) for visual aesthetics. If not resolved back to "fi", the word "ﬁnancial" is mathematically completely different from "financial", ruining vector embeddings and keyword search.
34. **Q: How did you handle repeated headers/footers that appeared on every single page?**
    *   **A:** Hardcoded regex failed because headers varied. Instead, I used a data-driven frequency analysis approach. The script counts every line in the document using Python's `collections.Counter().` Any line appearing exactly identical more than 8 times is mathematically flagged as noise (a header) and stripped out entirely.
35. **Q: Explain how you optimized PyMuPDF's table extraction process which was taking 20+ minutes.**
    *   **A:** `find_tables()` does expensive vector-math to detect intersecting lines on a page. I wrote a fast "pre-check" heuristic that first counts the total number of drawn line segments or rectangles on a page. If the page doesn't have at least 4 intersecting lines (the minimum for a 1-cell table), I instantly skip the expensive table calculation. This skipped ~80% of pages and brought processing time down to seconds.

### Advanced Data Engineering
36. **Q: Why did you decide to output 4 different files per PDF during ingestion?**
    *   **A:** Separation of concerns for different consumers. `.txt` is for human debugging. `.json (chunks)` is optimized for loading into the Database. `.json (tables)` is for raw programmatic data access. `.md (tables)` is pre-formatted specifically to be token-efficient for the LLM prompt.
37. **Q: What is Regex "Catastrophic Backtracking"?**
    *   **A:** When a poorly written regex with nested quantifiers (like `(a+)+$`) hits a string that almost matches but fails at the very end. The regex engine recursively attempts every possible permutation of the match, causing the CPU to hang indefinitely.
38. **Q: If a PDF consists of scanned images instead of digital text, what would you have to add to your pipeline?**
    *   **A:** Optical Character Recognition (OCR). I would need to integrate a library like Tesseract or AWS Textract to pass the raw images through a vision model to generate the text strings before my cleaning pipeline could start.

---

## Part 4: Backend & Database Operations

### Basic Backend
39. **Q: What is an ORM and what benefits does SQLAlchemy provide?**
    *   **A:** Object-Relational Mapping. It allows you to define database tables as Python Classes and interact with data using methods instead of writing raw SQL strings. It prevents SQL Injection, provides type hints, and allows for database-agnostic code.
40. **Q: What is a Pydantic model?**
    *   **A:** A data validation class used extensively in FastAPI. You define the expected types (e.g., `company: str`, `top_k: int`). If an API request comes in with invalid data, Pydantic immediately rejects it with a clear 422 Error before the code even runs.
41. **Q: Explain the Singleton pattern regarding how you managed the LLM Client.**
    *   **A:** Establishing an API client or loading a large ML model takes memory and time. Instead of recreating the class on every request, I used a global variable initialized to `None`. A helper function checks if it exists; if not, it instantiates it once. Every subsequent request uses the exact same instance in memory.

### Intermediate Backend
42. **Q: Explain how your In-Memory Cache works.**
    *   **A:** It's a Python dictionary stored at the module level. The "key" is a deterministic SHA-256 hash of the lowercased Query + Filters. The "value" is the full LLM response string alongside the source chunks. Before calling the LLM, the endpoint checks the cache.
43. **Q: What is a Cache TTL?**
    *   **A:** Time-To-Live. I timestamped every cache entry. When pulling an entry, I check if `current_time - timestamp > 3600 seconds`. If it is, the data is deleted and a fresh API call is made, ensuring users don't get stuck with stale answers indefinitely.
44. **Q: What is Cache Invalidation, and when does it happen in FinRAG?**
    *   **A:** It's forcefully clearing the cache when the underlying truth changes. In FinRAG, if the user hits `DELETE /api/documents/{id}` or uploads a new PDF, the entire dictionary cache is `.clear()`'ed. Otherwise, the system might confidently serve an LLM answer based on a deleted document.
45. **Q: How did you store the vector embeddings in SQLite?**
    *   **A:** SQLite doesn't have a native array type. I converted the numpy array of floats to a binary byte string `embedding.astype(np.float32).tobytes()` and stored it in a BLOB column. On retrieval, I parse the bytes back into a numpy array using `np.frombuffer()`. Binary is much smaller and faster to parse than JSON text.
46. **Q: What is SQLite WAL mode?**
    *   **A:** Write-Ahead Logging. Normally, SQLite locks the entire database when writing, blocking all readers. WAL mode writes changes to a separate log file first, allowing readers to continue querying the main DB concurrently without locking.

### Advanced Backend
47. **Q: How does a Python Generator (`yield`) facilitate SSE streaming?**
    *   **A:** A normal function `return`s once and ends. A generator with `yield` pauses its state, sends a chunk of data, and waits to be resumed. FastAPI takes this generator and streams each yielded string over the open HTTP connection as it becomes available, rather than waiting for the entire string to finish building in memory.
48. **Q: Explain API Rate Limiting and the Exponential Backoff pattern you implemented for Gemini.**
    *   **A:** Cloud APIs return HTTP 429 when you make too many requests. A simple retry might hit the server too fast again. Exponential backoff loops a retry `try/except` block, but the `time.sleep()` duration multiplies on each failure (e.g., 5s, 10s, 15s), giving the server's rate-limiting bucket time to refill.
49. **Q: You used `yield` for database sessions in FastAPI dependencies. Why?**
    *   **A:** `def get_session(): db = SessionLocal(); yield db; db.close()`. This ensures that exactly one database connection is opened per HTTP request, passed to the router, and *guaranteed* to close when the request finishes, preventing connection leaks.
50. **Q: How did you implement caching for the actual semantic chunk search?**
    *   **A:** I didn't! A cosine similarity dot product over 25k rows takes <100ms in RAM. Generating the LLM answer takes 4000ms. I focused caching strictly on the LLM generation step (which hashes the query+filter) because that was the true bottleneck determining UX latency.

---

## Part 5: Frontend & User Experience (UX)

### Basic Frontend
51. **Q: What is React State (`useState`)?**
    *   **A:** It's a hook that stores variables inside a component. When the state changes (like appending a new streaming word to the chat), React specifically re-renders only the HTML elements dependent on that state, rather than refreshing the whole page.
52. **Q: Why do API calls happen inside `useEffect`?**
    *   **A:** React re-renders components constantly. If you put `fetch()` directly in the component body, it would spam the server infinitely. `useEffect(..., [])` ensures the API call only happens exactly once when the component officially "Mounts" to the screen.
53. **Q: What is Tailwind CSS?**
    *   **A:** A utility-first CSS framework. Instead of writing custom CSS classes in separate files, you compose styles directly in the HTML using predefined atoms like `flex`, `p-4`, and `text-gray-500`. It ensures a perfectly consistent design system.
54. **Q: What is a SPA (Single Page Application)?**
    *   **A:** A web application where the browser loads a single HTML document. Navigation (like clicking 'Dashboard' to 'Ask') is handled entirely by JavaScript swapping out React components instantly, without requesting a new HTML page from the server.

### Intermediate Frontend
55. **Q: How did you build real-time streaming in the React client?**
    *   **A:** Instead of `await response.json()`, I used `response.body.getReader()` to access the raw byte stream of the SSE endpoint. Inside a `while(true)` loop, I used a `TextDecoder` to parse incoming bytes into text, extracted the JSON token, and appended it to the React `streamingText` state word-by-word.
56. **Q: What is the purpose of Skeleton Loaders?**
    *   **A:** To reduce *perceived* wait time and prevent Cumulative Layout Shift (CLS). By showing a shimmering gray outline of exactly where the text and cards *will* appear, the user's brain processes the page structure immediately, making the app feel significantly faster than looking at a blank screen with a spinning wheel.
57. **Q: How did you implement Glassmorphism in Tailwind?**
    *   **A:** By applying a semi-transparent background color (`bg-white/5` or `bg-gray-900/40`), a subtle border (`border border-white/10`), and most importantly, the CSS backdrop-filter (`backdrop-blur-md`), which mathematically blurs whatever falls behind the div, creating the "frosted glass" effect.
58. **Q: Why use `react-markdown` instead of just injecting HTML?**
    *   **A:** The LLM outputs Markdown text. You could parse it to HTML and use `dangerouslySetInnerHTML`, but that opens the app to Cross-Site Scripting (XSS) attacks. `react-markdown` safely parses exactly what is allowed and mounts them as safe React components.

### Advanced Frontend
59. **Q: Explain how you keep the chat window automatically scrolled to the bottom during a streaming response.**
    *   **A:** I created an invisible `<div>` at the very bottom of the chat list and attached a `useRef` to it. I added a `useEffect` that listens to changes in the `messages` array or `streamingText` state. Whenever they update, the effect calls `chatEndRef.current.scrollIntoView({ behavior: 'smooth' })`.
60. **Q: How did you implement conditional staggering of CSS entrance animations?**
    *   **A:** I defined a class `.animate-fade-in-up`. For lists (like search results), I dynamically generated delay classes like `stagger-1`, `stagger-2` based on the map `index`. In CSS, `.stagger-1` applies `animation-delay: 100ms`, `.stagger-2` applies `200ms`, creating a cascading waterfall entrance effect rather than having all cards appear simultaneously.

---

## Part 6: Fast-Fire Conceptual Questions

61. What does RAG stand for? *(Retrieval-Augmented Generation)*
62. What port does Uvicorn run on by default? *(8000)*
63. What is the HTTP status code for Rate Limiting? *(429)*
64. What is the HTTP status code for Validation Error in FastAPI? *(422 Unprocessable Entity)*
65. What does the `L6` mean in `all-MiniLM-L6-v2`? *(6 transformer layers)*
66. What algorithm calculates the angle between vectors? *(Cosine Similarity)*
67. What metric does BM25 use for term scaling? *(TF-IDF logic with saturation)*
68. What algorithm blends two search rank lists? *(Reciprocal Rank Fusion - RRF)*
69. What library handles PDF parsing in FinRAG? *(PyMuPDF / fitz)*
70. What React hook manages local component variables? *(useState)*
71. What React hook handles side effects like API calls? *(useEffect)*
72. What protocol streams text tokens to the frontend? *(Server-Sent Events - SSE)*
73. What database engine did you use? *(SQLite)*
74. What Python library maps objects to SQL? *(SQLAlchemy)*
75. What Python feature allows non-blocking server execution? *(async/await)*
76. What library validates FastAPI inputs? *(Pydantic)*
77. What regex removes purely empty lines? *( `\n{2,}` or `(\s*\n){3,}` )*
78. What caching policy deletes the oldest accessed items? *(LRU - Least Recently Used)*
79. What caching policy deletes items after a time limit? *(TTL - Time To Live)*
80. What UI technique blurs the background behind elements? *(Glassmorphism)*

---

## Part 7: Behavioral & "Show Your Work"

81. **Q: Tell me about a time you solved a massive performance bottleneck.**
    *   **A:** Detail the PyMuPDF `find_tables()` problem. It took 20 mins for large PDFs because it was doing vector math on every single page. Describe how you implemented a pre-check heuristic to count line segments first, skipping narrative pages and bringing processing time down to exactly 57 seconds.
82. **Q: How do you handle unexpected data quality issues?**
    *   **A:** Mention the typographic ligatures (`ﬁ` instead of "fi") found in the TCS reports that broke embedding matching. Explain that you don't just "hope" the data is fine—you wrote a specific Unicode normalizer step to map complex hex variants back to standard ASCII characters before vectorization.
83. **Q: Describe a feature you built to improve User Experience (UX).**
    *   **A:** Talk about ripping out the clunky 8-second waiting spinner and replacing it with Server-Sent Events (SSE). Describe the psychological difference for a user seeing text stream in instantly word-by-word versus waiting in silence.
84. **Q: Give an example of technical debt you accepted for velocity.**
    *   **A:** In-memory dictionary caching. For an MVP, installing Redis, configuring networks, and managing Docker containers is massive overhead. A module-level Python dict with TTL validation accomplishes the exact same goal locally with 20 lines of code. It's accepted technical debt that is cleanly encapsulated behind a `Cache` class, so swapping to Redis later won't break the app.
85. **Q: How did you ensure your system acts cleanly and predictably when errors occur?**
    *   **A:** Provide examples of FastAPI global exception handling, returning clean JSON error details (like "Cannot connect to database") rather than letting the server 500-crash and spew Python stack traces to the React frontend.

## Part 8: Deep Dives (Senior Knowledge Checks)

86. **Q: Can you explain the exact structure of a PyTorch / HuggingFace embedding space intuitively?**
    *   A: It is a 384-dimensional graph. Each dimension represents a latent semantic concept (e.g., "money-ness", "negative-sentiment-ness", "time-ness") learned during training. Vectors point to coordinates. The closer two points are in all 384 dimensions simultaneously, the more semantically related the original sentences are.
87. **Q: What is the risk of using external LLM APIs for financial data?**
    *   A: Data privacy and PII leakage. Sending proprietary, non-public 10-K drafts to Google Gemini violates compliance. In a real corporate setting, I would swap the `BaseLLMClient` to target a locally hosted model (like Llama-3 or Mistral) running on internal enterprise servers so data never leaves the VPC.
88. **Q: Why don't you just put the entire 100-page PDF into Gemini 1.5 Pro's 2-million token context window?**
    *   A: Three reasons: 1) Cost. Paying for 2 million tokens per question is prohibitively expensive. 2) Latency. Parsing a 2M token prompt takes 30-60+ seconds to generate the first token. 3) The "Lost in the Middle" phenomenon. Even advanced models struggle to accurately extract specific facts hidden deeply in massive context windows without hallucinating. RAG is cheaper, faster, and more accurate.
89. **Q: Explain how the Virtual DOM makes React fast.**
    *   A: Modifying the actual browser DOM is computationally expensive. React keeps a lightweight javascript copy (Virtual DOM). When state changes, React builds a NEW Virtual DOM, compares it to the old one (Diffing), identifies the exact minimal set of changes (e.g., just updating the text in one `<span>`), and paints *only* that change to the real DOM.
90. **Q: What is Dependency Injection and how does FastAPI use it?**
    *   A: Providing objects a function needs as arguments rather than instantiating them inside the function. In FastAPI `def endpoint(db: Session = Depends(get_session)):`, the framework executes `get_session`, injects the `db` connection, runs the endpoint, and cleans up the connection automatically. This makes endpoints incredibly easy to unit test by injecting fake mock-databases.

## Part 9: Lightning Round - "What tool would you use?"

91. If the SQLite file size grew to 100GB? -> *PostgreSQL with pgvector.*
92. If PDF uploads started taking 5 minutes and timing out HTTP requests? -> *Celery + RabbitMQ/Redis for asynchronous background jobs.*
93. If you needed to extract text from a scanned, image-only PDF? -> *Tesseract OCR or AWS Textract.*
94. If users complained the UI was looking messy on mobile phones? -> *Tailwind CSS media queries (`md:`, `lg:`) to implement responsive grid layouts.*
95. If the LLM started making up fake numbers? -> *Lower temperature to 0.0, strengthen the System Prompt grounding instructions, or use a larger model.*
96. If caching dicts consumed all server RAM? -> *Implement a dedicated caching layer like Redis with an eviction policy.*
97. If vector search accuracy was poor for highly technical questions? -> *Implement a Cross-Encoder Reranking step on the top 50 chunks.*
98. If different API requests needed to share a real-time state? -> *WebSockets via FastAPI.*
99. If you needed to deploy this project live tomorrow? -> *Dockerize the backend, build the Vite frontend, and deploy to AWS Elastic Beanstalk, Render, or Railway.*
100. If you needed to version your database schema as models changed? -> *Alembic (SQLAlchemy migration tool).*

## Part 10: Conclusion & Reflection

101. **Q: What was the most challenging bug you faced during the build?**
    *   A: (Discuss the unexpected whitespace formatting from PyMuPDF breaking the regex cleaners, or the realization that vector search was failing on exact acronyms requiring the pivot to Hybrid Search).
102. **Q: What are you most proud of in this architecture?**
    *   A: The end-to-end decoupling. The fact that the Data Pipeline, Vector Engine, LLM generation, REST API, and Frontend UI are entirely separate components. I can swap Gemini for OpenAI, SQLite for Postgres, or React for Vue, without breaking the other components.
103. **Q: What would you do differently if you built it again?**
    *   A: I would introduce `pgvector` from day one. SQLite BLOB storage is great for prototyping, but migrating chunk data format to a real vector database takes effort.
104. **Q: How does this project prove you are a Senior Full-Stack AI Engineer?**
    *   A: Because I didn't just string together LangChain abstractions. I built the Vector Math, the sliding-window chunker, the RAG prompt assembler, and the SSE HTTP streaming explicitly from scratch using base primitives and low-level libraries, proving I understand the mechanics of the entire stack.
105. **Q: Are you ready for the real interview?**
    *   A: Yes. 🚀

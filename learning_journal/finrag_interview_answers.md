# FinRAG — Interview Answers (Simple & Clear)

All answers are written the way you would actually speak in an interview. No fancy words. Just clear thinking.

---

## 1. Basic Screening Questions

**Q: Explain your project in 30 seconds.**
> I built a system called FinRAG where users can upload large financial PDFs like annual reports, and then ask questions about them in plain English. The system finds the most relevant paragraphs from those PDFs using a combination of vector search and keyword search, sends them to Google's Gemini LLM, and streams the answer back in real time with exact source citations.

**Q: What problem does FinRAG solve?**
> Financial reports are 100-300 pages long. Nobody reads the whole thing. FinRAG lets you just ask a question like "What was NVIDIA's revenue?" and get an accurate, cited answer in seconds — instead of scrolling through hundreds of pages.

**Q: Who is the target user of this system?**
> Financial analysts, investors, or anyone who needs to quickly pull specific data points from large company reports without reading them cover to cover.

**Q: What is RAG in simple terms?**
> RAG means Retrieval-Augmented Generation. Instead of letting the AI make up answers from its training data, we first search our own database for relevant text, then feed that text to the AI and say "answer using only this." So the AI reads our data and answers, rather than guessing.

**Q: What was your exact role in this project?**
> I built the entire project myself — the data pipeline, the backend API, the frontend UI, and all the AI/search logic. It was a solo learning project where I implemented everything from scratch.

**Q: How many documents did you process and what type?**
> 21 annual reports from 7 companies (like NVIDIA, JPMorgan, TCS, HDFC Bank). Total of about 5,350 pages. These are real financial PDFs — 10-Ks and annual reports.

**Q: What is the overall workflow from upload to answer?**
> User uploads a PDF → we extract text using PyMuPDF → clean it (remove headers, fix broken words) → split it into small chunks → convert each chunk into a vector using an embedding model → store everything in the database. When the user asks a question, we convert their question into a vector too, find the closest matching chunks, pass them to Gemini, and stream back the answer.

**Q: Why did you choose financial documents specifically?**
> Financial documents are perfect for RAG because they are long, data-heavy, and full of specific numbers. They are a good test because the AI needs to find exact figures, not just give vague summaries. It also makes the project relevant for real-world fintech use cases.

**Q: What was the biggest challenge you faced?**
> Text extraction from PDFs. The raw text from PyMuPDF was full of garbage — repeated headers on every page, broken hyphenated words, invisible control characters, and special characters like "ﬁ" instead of "fi". I had to build a 10-step cleaning pipeline to fix all of this before the data was usable.

**Q: What would you improve if you had more time?**
> Three things: 1) Move from SQLite to PostgreSQL with pgvector for proper vector database support. 2) Add a reranking step using a Cross-Encoder model to improve retrieval accuracy. 3) Add an analytics dashboard that extracts key financial metrics and visualizes them as charts.

---

## 2. Architecture & Design Questions

**Q: Can you draw and explain the architecture of your system?**
> There are three main parts. The React frontend talks to the FastAPI backend through REST APIs. The backend has three layers: the ingestion pipeline (PDF → chunks → embeddings), the search engine (vector + BM25 hybrid), and the RAG pipeline (search → prompt → LLM → answer). Everything is stored in an SQLite database.

**Q: Why did you choose a RAG architecture instead of fine-tuning?**
> Fine-tuning means retraining the entire model on your data. That is expensive, slow, and the model can still hallucinate. With RAG, I don't touch the model at all. I just give it the right context at query time. It is cheaper, faster to update (just upload a new PDF), and the answers are grounded in actual text with citations.

**Q: How does data flow from frontend to LLM and back?**
> User types a question in React → React sends a POST request to FastAPI → FastAPI converts the question to a vector → searches the database for matching chunks → builds a prompt with those chunks → sends it to Gemini → Gemini streams tokens back → FastAPI forwards each token as an SSE event → React displays each word as it arrives.

**Q: Why did you separate frontend and backend?**
> Because they do completely different jobs. The frontend handles UI and user interaction. The backend handles heavy computation like embedding, searching, and calling the LLM. Separating them means I can deploy them independently, scale them independently, and even swap React for a mobile app later without changing any backend code.

**Q: What are the main components of your system?**
> 1) PDF ingestion pipeline (extract, clean, chunk). 2) Embedding engine (converts text to vectors). 3) Search engine (hybrid vector + BM25). 4) RAG pipeline (search → prompt → LLM). 5) FastAPI REST API. 6) React frontend with streaming chat UI.

**Q: Where does vector search happen?**
> In the backend. When a query comes in, the embedding model converts it to a 384-dimension vector. Then I load all stored chunk vectors from SQLite into a numpy array and compute the dot product (cosine similarity) between the query vector and every chunk. The highest-scoring chunks are the most relevant.

**Q: How do you handle large documents?**
> I split them into smaller pieces called "chunks" — about 1000 characters each with 200 characters of overlap. This way, each chunk is small enough to be meaningful for search, but the overlap ensures no important sentence gets cut in half at a boundary.

**Q: What happens when a query is received step by step?**
> 1) Check the cache — if we answered this exact question before, return instantly. 2) Auto-detect if a company name is in the query (like "TCS"). 3) Convert the query to a vector. 4) Run vector search AND BM25 keyword search. 5) Combine results using Reciprocal Rank Fusion. 6) Take top 5 chunks. 7) Build a prompt with those chunks. 8) Send to Gemini. 9) Stream the answer back to the user token by token.

**Q: How does SSE streaming improve UX?**
> Without streaming, the user stares at a blank screen for 5-8 seconds waiting for the full answer. With SSE, the first words appear within 1 second and the rest flow in smoothly. It feels much faster and more interactive, even though the total time is the same.

**Q: How does your caching layer work?**
> I hash the user's query and filters into a unique key. If the same question was asked before and the cache hasn't expired (TTL of 1 hour), I return the stored answer instantly — no search, no LLM call. If a document is uploaded or deleted, the entire cache is cleared so we never serve stale answers.

**Q: What is the bottleneck in your architecture?**
> The LLM API call. Search takes under 100ms. But waiting for Gemini to generate a full answer takes 3-8 seconds. That is why I implemented streaming — so the user sees progress immediately instead of waiting for the full response.

**Q: How would the system behave with 10x users?**
> SQLite would struggle because it locks the entire file during writes. The in-memory cache is per-process, so multiple server instances wouldn't share it. I would need to switch to PostgreSQL for the database and Redis for shared caching. The embedding model loading would also need to be optimized.

**Q: Where would you add load balancing?**
> In front of multiple FastAPI server instances. A reverse proxy like Nginx or a cloud load balancer would distribute incoming requests across 3-4 backend servers. Each server would connect to the same PostgreSQL database and the same Redis cache.

---

## 3. Tech Stack Justification

### Backend

**Q: Why did you choose FastAPI over Flask or Node?**
> FastAPI supports async/await natively. When my server is waiting 5 seconds for Gemini to respond, it can handle other users' requests in the meantime. Flask is synchronous by default — it would block. FastAPI also gives me automatic input validation through Pydantic and free Swagger API docs, which Flask doesn't have out of the box.

**Q: Why Python for backend instead of Node (since you know MERN)?**
> All the AI/ML libraries I needed — SentenceTransformers, PyMuPDF, numpy, rank_bm25 — are Python libraries. The entire machine learning ecosystem lives in Python. Using Node would mean I'd have to call Python scripts from Node, which adds unnecessary complexity.

**Q: How does FastAPI handle async requests?**
> When you define an endpoint with `async def`, FastAPI uses Python's asyncio event loop. When the code hits an `await` (like waiting for the Gemini API), it pauses that request and picks up another one. When the API response arrives, it resumes the first request. This way one slow API call doesn't block the whole server.

**Q: How did you structure your API routes?**
> I used FastAPI's Router system. I have separate router files for documents (list/delete), upload (file ingestion), and search (semantic search + RAG). Each router handles one area of responsibility. They all get included in the main app via `app.include_router()`.

### Frontend

**Q: Why React instead of plain JS or Next.js?**
> Plain JS would be painful for a chat interface where the UI constantly updates as new tokens stream in. React's state management and component system handle that perfectly. I didn't need Next.js because I'm not doing server-side rendering — my app is a pure client-side SPA that talks to a separate FastAPI backend.

**Q: How did you manage state?**
> Using React's built-in `useState` hook. I have state for the chat messages array, the current streaming text, the loading status, and the input field value. When a new token arrives from SSE, I update the streaming text state, and React automatically re-renders just that part of the UI.

**Q: How did you handle streaming responses in UI?**
> Instead of `await response.json()`, I used `response.body.getReader()` to read the raw byte stream. In a loop, I decode each chunk with `TextDecoder`, parse the SSE data lines, extract the token, and append it to the React state. The UI updates with each new word.

### Database

**Q: Why SQLite for this project?**
> Zero setup. No installation, no server to run, no configuration. Just a single file (`finrag.db`). For a learning project and local development, it is perfect. And because I used SQLAlchemy (an ORM), my code is database-agnostic — switching to PostgreSQL later means changing just one connection string.

**Q: When would SQLite fail?**
> When you have multiple users writing to the database at the same time. SQLite locks the entire file during writes. Also, on cloud platforms like Render, the file system is wiped on every restart, so you'd lose all your data.

**Q: If scaling, what database would you switch to?**
> PostgreSQL with the pgvector extension. PostgreSQL handles concurrent reads/writes well, and pgvector adds native vector similarity search so I wouldn't need to load all embeddings into RAM. I could also use a managed service like Supabase or Neon for zero maintenance.

### LLM

**Q: Why Gemini LLM?**
> It has a generous free tier, good performance for factual Q&A, and a simple Python SDK. For a personal project, cost matters. Gemini gave me enough free API calls to develop and test without paying anything.

**Q: How would the system change if you used OpenAI or local LLM?**
> Almost nothing would change in the core code. I used the Strategy pattern — there's a `BaseLLMClient` interface and a `GeminiClient` implementation. To switch to OpenAI, I'd just create an `OpenAIClient` class implementing the same interface and change one config variable. The rest of the pipeline stays identical.

---

## 4. RAG Deep Concept Questions

**Q: What are the main components of a RAG pipeline?**
> Three parts: Retrieval (find relevant chunks from the database), Augmentation (inject those chunks into the prompt as context), and Generation (the LLM reads that context and generates an answer).

**Q: What is embedding and why is it needed?**
> An embedding converts text into a list of numbers (a vector). Computers can't understand words, but they can compare numbers. If two sentences have similar meaning, their vectors will be close together. This is how we find relevant text without exact keyword matching.

**Q: What embedding model did you use?**
> `all-MiniLM-L6-v2` from HuggingFace. It outputs 384-dimensional vectors. It's small (80MB), fast, and has one of the best performance-to-speed ratios on the MTEB benchmark.

**Q: What is vector similarity search?**
> Convert the user's question into a vector. Then compare it against all stored chunk vectors using cosine similarity (basically measuring how similar two vectors are). The chunks with the highest similarity scores are the most relevant to the question.

**Q: Difference between semantic search and keyword search?**
> Keyword search matches exact words — "revenue" only finds "revenue". Semantic search matches meaning — "revenue" also finds "income", "sales", "earnings" because their vectors are close together. But semantic search can miss exact acronyms like "ESG" that keyword search catches easily.

**Q: Why did you use hybrid search (BM25 + vectors)?**
> Because neither is perfect alone. Vector search is great for meaning but misses exact keywords. BM25 is great for exact terms but misses synonyms. I combine both and use Reciprocal Rank Fusion to merge their results. This gives me the best of both worlds.

**Q: How do you evaluate retrieval quality?**
> I manually check if the top retrieved chunks actually contain the answer to the question. If I ask "NVIDIA revenue 2024" and the top chunks are about NVIDIA's revenue section, the retrieval is good. In a production system, you'd use metrics like Mean Reciprocal Rank (MRR) or Recall@K.

**Q: What is chunking and how did you choose chunk size?**
> Chunking means splitting a large document into smaller pieces. I chose 1000 characters with 200 overlap. Too small and the chunk lacks context. Too large and it includes irrelevant info that dilutes the search. 1000 characters captures roughly one complete paragraph or idea.

**Q: What happens if chunk size is too large or too small?**
> Too small: the chunk might say "$60.9 billion" with no context about what that number refers to. Too large: a 5000-character chunk might talk about revenue, risks, AND employees — making it less precise for any single query. It also wastes the LLM's context window.

**Q: How do you prevent hallucinations?**
> Two ways. First, the system prompt tells the LLM: "Only answer using the provided context. If the information is not there, say you don't know." Second, I format sources as [Source 1], [Source 2] and tell the LLM to cite them. This grounds every claim in actual text.

**Q: How would you implement reranking?**
> After the initial fast retrieval of top 50 chunks, I would pass each chunk along with the query through a Cross-Encoder model (like Cohere Rerank). A Cross-Encoder reads the query and chunk together through attention layers, giving a much more accurate relevance score. Then I pick the final top 5 from that. It's slower but more precise.

**Q: What is cosine similarity mathematically?**
> It measures the angle between two vectors. The formula is: dot product of A and B, divided by the product of their lengths. If both vectors are normalized (length = 1), it simplifies to just the dot product. A score of 1.0 means identical, 0.0 means unrelated.

**Q: How does BM25 scoring work conceptually?**
> BM25 scores a document based on how many times the search terms appear in it, but with two adjustments: 1) Term frequency saturates — mentioning a word 100 times isn't much better than 10 times. 2) Document length matters — finding a word in a short document is a stronger signal than finding it in a huge one.

**Q: How do you measure answer faithfulness?**
> In a production system, you'd use a separate LLM call to check: "Does this answer only contain information present in the provided sources?" This is called LLM-as-a-judge. For my project, I verified manually by checking if the cited sources actually support the claims in the answer.

---

## 5. Backend & API Questions

**Q: How many endpoints did you create?**
> About 6 main ones: GET /api/documents (list all), DELETE /api/documents/{id} (remove one), POST /api/upload (ingest a PDF), POST /api/search (semantic search only), POST /api/ask (full RAG answer), and POST /api/ask/stream (streaming RAG with chat history).

**Q: How did you handle file uploads?**
> FastAPI has a built-in `UploadFile` type. The user selects a PDF in the React frontend, it gets sent as multipart form data. The backend saves it temporarily, runs the full ingestion pipeline (extract → clean → chunk → embed → store in DB), and then returns a success response.

**Q: How did you process PDFs?**
> Using PyMuPDF (imported as `fitz`). It reads each page and extracts the raw text. Then I run a 10-step cleaning pipeline to fix all the PDF artifacts — broken words, repeated headers, invisible characters, ligatures. After cleaning, I split the text into overlapping chunks.

**Q: How did you implement caching?**
> A Python dictionary at the module level. The key is a SHA-256 hash of the normalized query + filters. The value is the full answer + sources + a timestamp. Before calling the LLM, I check the cache. If the entry exists and hasn't expired (1 hour TTL), I return it instantly. If a document is uploaded or deleted, I clear the entire cache.

**Q: What data structure stores embeddings?**
> Each embedding is a numpy array of 384 floats. For storage in SQLite, I convert it to raw bytes using `.tobytes()` and store it as a BLOB column. When I need to search, I load all embeddings back into numpy arrays and compute dot products.

**Q: How did you handle errors?**
> FastAPI lets you raise `HTTPException` with proper status codes. If a document ID doesn't exist, I return 404. If validation fails, Pydantic automatically returns 422. For the LLM API, I wrapped calls in try/except with retry logic — if Gemini returns a 429 (rate limit), I wait and retry up to 3 times.

**Q: How did you test your APIs?**
> FastAPI auto-generates Swagger docs at `/docs`. I used that to manually test every endpoint — upload files, run searches, ask questions. I also tested directly from the React frontend and checked the terminal logs for any errors.

**Q: How does SSE differ from WebSockets?**
> SSE is one-way: server pushes data to the client over a normal HTTP connection. WebSockets are two-way: both sides can send data anytime. For streaming an LLM response, I only need one-way (server to client), so SSE is simpler and sufficient. No need for the overhead of WebSockets.

**Q: How would you secure the API?**
> Add JWT-based authentication. Users would log in to get a token, and every API request would include that token in the Authorization header. FastAPI has built-in support for OAuth2 and JWT through its dependency injection system.

**Q: How would you add authentication?**
> Create a `/login` endpoint that validates credentials and returns a JWT token. Then add a `Depends(get_current_user)` dependency to protected endpoints. FastAPI checks the token automatically before running the endpoint code.

**Q: How would you rate limit requests?**
> Use a library like `slowapi` which integrates with FastAPI. You can set rules like "10 requests per minute per IP address." For the LLM endpoint specifically, this also helps control API costs.

---

## 6. Performance & Scalability Questions

**Q: What is the slowest step in your pipeline?**
> The LLM API call. It takes 3-8 seconds. Everything else — search, prompt building, even embedding the query — happens in under 200ms. That's why I added caching and streaming specifically for the LLM step.

**Q: How long does a typical query take?**
> First query: about 6-7 seconds (includes loading the embedding model). After that: 3-5 seconds if not cached (mostly LLM wait time), or near-instant if cached.

**Q: How did you optimize retrieval speed?**
> Three things: 1) I normalize all embeddings at storage time so cosine similarity becomes a simple dot product. 2) I use numpy for vectorized matrix multiplication instead of looping through chunks one by one. 3) I denormalized company/year into the chunks table so filtering doesn't need expensive JOINs.

**Q: How would you scale this system to enterprise level?**
> Switch SQLite to PostgreSQL with pgvector. Replace the in-memory Python dict cache with Redis. Move PDF processing to background workers using Celery. Deploy multiple FastAPI instances behind a load balancer. Add proper authentication and rate limiting.

**Q: How would you handle millions of documents?**
> At that scale, loading all vectors into RAM won't work. I'd use a dedicated vector database like Pinecone, Weaviate, or pgvector. These use approximate nearest neighbor (ANN) algorithms like HNSW to search billions of vectors in milliseconds without loading everything into memory.

**Q: Would you move embeddings to a vector DB? Which one?**
> Yes, if the dataset grows beyond 100K chunks. I'd use pgvector (PostgreSQL extension) because we already use SQL, so the migration is smooth. For even larger scale, Pinecone or Weaviate are managed services that handle billions of vectors.

**Q: How would you implement horizontal scaling?**
> Run multiple copies of the FastAPI server behind a load balancer (like Nginx). They all connect to the same PostgreSQL database and the same Redis cache. Each instance is stateless — any instance can handle any request. This is why separating state (DB, cache) from compute (API servers) matters.

---

## 7. Real-World Production Questions

**Q: How would you deploy this system?**
> Frontend on Vercel (free, instant deploys for React). Backend on Render or Railway (supports Python). Database on Supabase or Neon (free managed PostgreSQL). I'd set environment variables for the API key and database URL on each platform.

**Q: How would you monitor errors?**
> Add a logging service like Sentry. It captures every unhandled exception with full stack traces, and sends alerts. For custom monitoring, I'd log every LLM request with the query, response time, and whether it was a cache hit or miss.

**Q: How would you log LLM responses?**
> Store every question, the retrieved chunks, the LLM's answer, and the response time in a separate logging table. This helps with debugging bad answers, tracking costs, and building evaluation datasets over time.

**Q: How would you handle sensitive financial data?**
> In a real corporate setting, I would not send data to an external API like Gemini. I'd host a local LLM (like Llama or Mistral) on the company's own servers so no data leaves the network. I'd also encrypt the database and add role-based access control.

**Q: How would you implement access control?**
> Different users see different documents. Add a `user_id` column to the documents table. When a user searches, filter chunks to only show results from documents they have access to. Admin users can see everything.

**Q: How would you ensure reliability?**
> Health check endpoints (`GET /api/health`), automatic restarts on crash (handled by the hosting platform), retry logic for external API calls, and graceful error messages instead of raw stack traces.

---

## 8. Edge Cases & Failure Scenarios

**Q: What happens if the LLM API fails?**
> I have retry logic with exponential backoff — wait 5s, then 10s, then 15s. If all 3 retries fail, the API returns a clean error message to the frontend like "The AI service is temporarily unavailable. Please try again." The user never sees a raw error.

**Q: What happens if no relevant chunks are found?**
> The search still returns the top 5 chunks, but their similarity scores will be very low (below 0.3). The prompt tells the LLM to say "I don't have sufficient information in the provided documents" when the context doesn't contain the answer. So the LLM gracefully declines instead of making something up.

**Q: How do you handle very large PDFs?**
> The chunking step handles it automatically — a 300-page PDF just produces more chunks. The only issue was table extraction speed, which I solved with a pre-check heuristic that skips pages without enough drawn lines, cutting processing time dramatically.

**Q: What if the user asks unrelated questions?**
> Like "What's the weather today?" — the retrieved chunks will be about financial data, which has nothing to do with weather. The system prompt says "only answer from the provided context," so the LLM will respond with "I don't have information about that in the provided documents."

**Q: How do you avoid repeated indexing?**
> Before inserting a document, I check if a file with the same name already exists in the database. If it does, I skip it. This makes the pipeline idempotent — you can run it multiple times safely without creating duplicates.

---

## 9. Comparison Questions

**Q: RAG vs Fine-tuning — when to use each?**
> RAG: when your data changes often (new reports every quarter), when you need citations, when you want to avoid training costs. Fine-tuning: when you need the model to learn a specific style or domain permanently, like medical terminology or legal language. For financial Q&A with changing data, RAG is the clear choice.

**Q: Vector DB vs traditional DB?**
> Traditional DBs (SQL) are great for exact lookups — "find all documents where company = TCS." Vector DBs are built for similarity search — "find text chunks most similar in meaning to this query." In FinRAG, I use a traditional DB (SQLite) but do vector math manually in Python. At scale, I'd use pgvector to get both in one database.

**Q: SSE vs WebSockets?**
> SSE: one-way (server to client), simpler, works over normal HTTP, auto-reconnects. WebSockets: two-way, more complex, needs special protocol. For streaming an LLM response, SSE is enough because only the server is sending data. WebSockets would be overkill.

**Q: FastAPI vs Node?**
> For an AI project, FastAPI wins because all the ML libraries (PyTorch, SentenceTransformers, numpy) are in Python. Node would require calling Python as a subprocess, adding complexity. FastAPI also has native async support and automatic validation that Express.js doesn't provide out of the box.

**Q: Hybrid search vs vector-only search?**
> Vector-only misses exact keywords. If someone searches "ESG compliance" and the document uses the exact term "ESG", BM25 will find it perfectly while vector search might rank it lower because it focuses on the broader concept. Hybrid catches both semantic meaning AND exact terms.

---

## 10. Behavioral + Ownership Questions

**Q: What did you personally build vs learn?**
> I built every part myself — the pipeline, the API, the frontend, the search logic. I used AI tools for guidance and debugging when I got stuck, but I understood and wrote every line of code. The learning was hands-on — I didn't just follow a tutorial.

**Q: What was the hardest bug?**
> The text cleaning pipeline. I thought extracted PDF text was clean, but it had invisible characters, repeated headers appearing 300 times, and special unicode ligatures that broke my embeddings. I had to build a 10-step cleaner and run quality audits to catch things that were invisible to the human eye.

**Q: What tradeoffs did you make?**
> SQLite instead of PostgreSQL — faster to develop but won't scale. In-memory dict cache instead of Redis — simpler but per-process only. Manual cosine similarity instead of a vector database — educational but won't work for millions of chunks. All of these are deliberate tradeoffs I can fix when scaling.

**Q: What did this project teach you about real systems?**
> That data cleaning is 80% of the work. That raw PDF text is never clean. That vector search alone isn't enough — you need keyword search too. That users care about perceived speed (streaming) as much as actual speed. And that separating components cleanly makes everything easier to change later.

**Q: If your team had 3 more engineers, what would you build next?**
> One person would build the analytics dashboard (extract financial metrics into charts). One would handle deployment and monitoring (Docker, CI/CD, Sentry). One would add authentication, access control, and multi-tenant support so different companies can use the system with their own private documents.

---

## 11. Critical / Negative / "Poking Holes" Questions

These are the toughest questions. Interviewers ask these to see if you are honest, self-aware, and can think beyond what you built.

---

### "Why not just use ChatGPT?"

**Q: A user can just upload a PDF to ChatGPT and ask questions. Why would anyone use your system instead?**
> Fair point. ChatGPT works great for one-off questions on a single file. But FinRAG solves a different problem. It lets you upload 20+ documents, store them permanently in a searchable database, and ask questions across all of them at once. ChatGPT doesn't remember files across sessions, can't do cross-document comparison, and doesn't let you filter by company or year. Also, ChatGPT is a black box — you don't know which part of the PDF it read. FinRAG gives exact source citations so you can verify every answer.

**Q: ChatGPT has a 2 million token context window now. Why even bother with RAG?**
> Three reasons. 1) Cost — sending 2 million tokens per question is very expensive. 2) Speed — processing a 2M token prompt takes 30-60 seconds before the first word appears. 3) Accuracy — research shows LLMs struggle with the "lost in the middle" problem, where they miss facts buried deep inside huge context windows. RAG is cheaper, faster, and more precise because it only sends the 5 most relevant paragraphs, not the entire document.

---

### "What you should have done but didn't"

**Q: Why didn't you use a proper vector database like Pinecone or ChromaDB?**
> Because at 25,000 chunks, loading everything into numpy and computing dot products takes under 100ms in RAM. Adding Pinecone would introduce network latency, an external dependency, and a paid service — all for zero speed improvement at this scale. But I'm fully aware that beyond 100K-500K chunks, I'd need to switch to pgvector or Pinecone because RAM loading won't scale.

**Q: Why didn't you write any unit tests?**
> Honest answer — I focused on building features and learning the architecture. In a production project, I would absolutely write tests. I'd use `pytest` for the backend (testing the RAG pipeline, search, and API endpoints) and something like Vitest or React Testing Library for the frontend. It's a gap I'm aware of.

**Q: Why didn't you use LangChain or LlamaIndex? They do all of this for you.**
> That was a deliberate decision. Frameworks like LangChain abstract everything away. If I used LangChain, I'd call `RetrievalQA.from_chain_type()` and it would work — but I wouldn't understand how the vector search, prompt building, or streaming actually works under the hood. I built it from scratch specifically to learn the internals. In a production team, I'd definitely consider using a framework for speed.

**Q: Why didn't you add authentication or user login?**
> Because the core learning goal was the RAG pipeline, not user management. Adding JWT auth is a well-understood pattern I've done in my MERN project (Cartix). I kept FinRAG focused on the AI and search complexity. But I know exactly how I'd add it — FastAPI has built-in OAuth2 support with `Depends()` for protecting routes.

**Q: You don't have any evaluation metrics. How do you know your system actually works well?**
> You are right, I don't have automated evaluation. I tested manually — asking questions and checking if the retrieved chunks contain the right answer and if the citations are accurate. For production, I would build an evaluation dataset (50-100 question-answer pairs), and measure metrics like Recall@5 (did the correct chunk appear in the top 5?) and answer faithfulness (does the LLM's answer match the source text?).

**Q: You used the free tier of Gemini. What if Google changes their pricing or limits tomorrow?**
> That's a real risk with any external API. That's exactly why I built the Strategy pattern with `BaseLLMClient`. If Gemini's free tier disappears, I swap in an `OpenAIClient` or even a local model like Ollama running Llama-3. The rest of the codebase doesn't change at all. I designed for this exact scenario.

---

### "Your system is weak because..."

**Q: Your search loads ALL 25,000 vectors into memory every time. That's terrible for performance, isn't it?**
> At 25K chunks with 384-dimensional vectors, the total memory is about 37MB. Loading and computing dot products on that takes under 100ms. So right now, it's actually fine. But yes, at 1 million chunks that becomes 1.5GB of RAM per request, which is not sustainable. At that point I'd move to pgvector or Pinecone, which use HNSW indexing to search without loading everything.

**Q: Your cache invalidation is too aggressive. You clear the ENTIRE cache when one document is uploaded. Why not be smarter?**
> You are right — it's a brute-force approach. A smarter system would only invalidate cache entries that reference chunks from the affected document. I chose the simple approach because: 1) the cache rebuilds quickly (one LLM call), and 2) for a small-scale system, the simplicity is worth more than the optimization. But I understand the tradeoff.

**Q: What if two people upload the same PDF with different filenames? You'd get duplicate data.**
> Good catch. Right now I check for duplicate `file_name`. If someone uploads the same content as `report_v1.pdf` and `report_v2.pdf`, both would get indexed. A better approach would be to hash the file content (like SHA-256 of the PDF bytes) and check for content-level duplicates, not just filename.

**Q: Your text cleaning pipeline has 10 steps. Isn't that fragile? What if the order changes?**
> The order matters a lot. For example, Unicode normalization (Step 1) must happen before regex matching (Step 4), because regex won't match ligature characters. I documented each step and why it's in that position. It's not fragile — it's sequential by design. Each step has a clear purpose and they build on each other.

---

### "Prove you understand the theory"

**Q: You say you used cosine similarity. But what happens if your embeddings are NOT normalized?**
> Then plain dot product gives you wrong results because longer vectors get unfairly high scores. Cosine similarity fixes this by dividing by the vector magnitudes. In my code, I pass `normalize_embeddings=True` when encoding, so all vectors have length 1. After that, cosine similarity equals the dot product, which is faster to compute.

**Q: Can your system handle PDFs in Hindi or other languages?**
> Not well right now. The embedding model `all-MiniLM-L6-v2` is trained primarily on English text. For Hindi PDFs, I'd need a multilingual embedding model like `paraphrase-multilingual-MiniLM-L12-v2` from HuggingFace. The rest of the pipeline (extraction, chunking, search) would work the same.

**Q: What if two companies report very different things under the same heading "Revenue"? Would your search get confused?**
> This is exactly why I built company auto-detection and filtering. If the user says "TCS revenue", my system detects "TCS" and filters chunks to only that company before searching. Without this filter, yes — NVIDIA's revenue chunks might outrank TCS's because NVIDIA's numbers appear more frequently in the dataset.

---

### "Honesty & Self-awareness"

**Q: What is the weakest part of your project?**
> The lack of automated testing and evaluation metrics. I can tell you it works from manual testing, but I can't give you a precision or recall number. In a real job, I would build a ground-truth evaluation set first and measure performance before and after every change.

**Q: Is this project production-ready?**
> No, and I wouldn't claim it is. It's missing authentication, proper error monitoring, automated tests, database migrations, Docker containerization, and HTTPS. It's a fully working prototype that demonstrates the complete architecture. Making it production-ready would be the next phase.

**Q: Did you use AI tools to help you build this?**
> Yes. I used AI for guidance on architecture decisions, debugging errors, and understanding new concepts. But I wrote and understood every line of code. I can explain any file in the project and trace any request through the full system. The learning was real — the AI was like a smart textbook, not a copy-paste source.

**Q: What would a senior developer criticize about your code?**
> Probably: no tests, no Docker, no CI/CD pipeline, cache invalidation is too aggressive, and the vector search won't scale past 100K chunks. All valid points. I'm aware of each one and I know how to fix them. The goal of this project was learning the RAG architecture end-to-end, not building a production SaaS product.

**Q: If you were hiring someone and they showed you this project, what would impress you and what wouldn't?**
> I'd be impressed that they built the full stack from scratch — PDF processing, vector search, LLM integration, streaming, and a React chat UI. That's a lot of surface area. I wouldn't be impressed if they couldn't explain how cosine similarity works or why they chose BM25 over just vector search. The code matters less than the understanding behind it.

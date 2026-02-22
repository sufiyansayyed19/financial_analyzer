# FinRAG: Mid-Project Recap
*A step-by-step summary of the architecture and features built so far.*

We have successfully built a complete **Retrieval-Augmented Generation (RAG)** system from scratch, focusing on processing dense financial documents (like Annual Reports) and answering user questions with exact citations. 

Here is exactly what we have built, layer by layer:

---

## 1. The Data Ingestion Layer (Phase 1)
* **PDF Extraction:** We used `PyMuPDF` to crack open dense financial PDFs, extracting raw text while skipping empty pages or purely visual elements.
* **Text Cleaning:** We built a robust text cleaner that removes weird characters (ligatures), standardizes whitespace, strips out tiny/irrelevant lines, and prepares the text for NLP tasks.
* **Chunking Engine:** We implemented a "sliding window" chunking strategy. Because a 100-page report can't fit into an LLM's prompt, we cut the document into smaller pieces (chunks) of ~1000 characters with a 200-character overlap. This overlap ensures we don't accidentally cut a crucial sentence in half.

## 2. The Vector & Database Layer (Phase 2)
* **Embedding Model:** We used `SentenceTransformers` (specifically the `all-MiniLM-L6-v2` model) to convert our text chunks into numerical vectors (384 dimensions). This allows computers to understand the *meaning* of the text, not just the exact words.
* **Database Storage:** We set up an `SQLite` database using `SQLAlchemy`. When a PDF is uploaded, we save its metadata (Company, Year) in one table, and all its individual text chunks (along with their binary vector embeddings) in another.
* **Semantic Search:** We wrote a search engine that takes a user's question, converts it into a vector, and compares it against all chunk vectors in our database using **Cosine Similarity**. This finds the chunks most conceptually related to the question.

## 3. The LLM & Generation Layer (Phase 3)
* **Gemini Client:** We connected to Google's Gemini API (using the brand new `google-genai` SDK) to act as our reasoning engine.
* **The RAG Prompt Builder:** We tell Gemini to act as an expert financial analyst. When a user asks a question, we retrieve the top 5 most relevant chunks from step 2 and inject them directly into the prompt.
* **Strict Citations:** We instructed the LLM to *only* answer using the provided context and to append exact citations (e.g., `[Source 1]`) at the end of every claim, preventing hallucinations.

## 4. The Backend API Layer (Phase 5)
* **FastAPI Setup:** We wrapped all of our Python logic into a blazing-fast REST API server using `FastAPI` and `Uvicorn`.
* **Endpoints:** We created endpoints to:
    * `POST /api/upload`: Accept raw PDF files, process them through the ingestion engine, and save them to the database.
    * `GET /api/documents`: List all processed documents.
    * `DELETE /api/documents/{id}`: Remove a document and clear its chunks.
    * `POST /api/search`: Run the semantic search engine and return raw source chunks.
    * `POST /api/ask`: The main endpoint that triggers the full RAG pipeline and streams back the AI's formulated answer.

## 5. The Frontend Dashboard Layer (Phase 7)
* **React & Vite:** We spun up a modern Single Page Application (SPA) using React and Vite for a lightning-fast UI.
* **Glassmorphism Design:** We styled the app using `Tailwind CSS`, enforcing a beautiful, dark-mode, glass-like aesthetic perfectly suited for modern AI products.
* **Dynamic Ask & Search UI:** We built a user interface that lets you dynamically filter queries by the exact companies and years currently stored in your database (fetching this info live from the API!).
* **Results Display:** The UI neatly separates the AI's conversational response from a grid of "Source Cards" that let users see exactly which document chunks informed the answer.

---

### Total Result So Far
You can drop a massive 100-page Tesla Annual Report into the UI, wait a few seconds, and then ask *"What were Tesla's primary risk factors regarding lithium supply chains in 2024?"* 

The system will instantly fish out the exact paragraphs mentioning lithium from the depths of the document and synthesize a clean, cited answer on the spot.

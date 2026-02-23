"""
🧠 FinRAG — API Schemas
=========================

WHAT THIS DOES:
---------------
Defines the SHAPE of all API requests and responses using Pydantic.

WHY PYDANTIC SCHEMAS?
──────────────────────
Without schemas:
  @app.post("/ask")
  async def ask(request):
      question = request["question"]  # No validation, crashes on typo

With schemas:
  @app.post("/ask")
  async def ask(request: AskRequest):
      question = request.question  # Auto-validated, IDE autocomplete

Pydantic automatically:
  1. Validates types (string, int, etc.)
  2. Returns clear error messages for invalid data
  3. Generates OpenAPI/Swagger docs automatically
  4. Provides IDE autocomplete

WHAT YOU'LL LEARN:
- Pydantic models for API contracts
- Request vs Response separation
- Optional fields with defaults
"""

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# 📥 REQUEST MODELS
# ──────────────────────────────────────────────

class AskRequest(BaseModel):
    """Request body for the /api/ask endpoint (RAG Q&A)."""
    question: str = Field(..., description="Natural language question", min_length=3)
    company: str | None = Field(None, description="Filter by company (e.g., 'nvidia')")
    year: str | None = Field(None, description="Filter by year (e.g., '2024')")
    region: str | None = Field(None, description="Filter by region (e.g., 'us')")
    top_k: int = Field(5, description="Number of sources to retrieve", ge=1, le=20)


class ChatMessage(BaseModel):
    """A single message in a conversation."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class ChatRequest(BaseModel):
    """Request body for the /api/ask/stream endpoint (streaming + chat history)."""
    question: str = Field(..., description="Current question", min_length=3)
    history: list[ChatMessage] = Field(default_factory=list, description="Previous messages")
    company: str | None = Field(None, description="Filter by company")
    year: str | None = Field(None, description="Filter by year")
    region: str | None = Field(None, description="Filter by region")
    top_k: int = Field(5, description="Number of sources to retrieve", ge=1, le=20)


class SearchRequest(BaseModel):
    """Request body for the /api/search endpoint."""
    query: str = Field(..., description="Search query", min_length=2)
    company: str | None = Field(None, description="Filter by company")
    year: str | None = Field(None, description="Filter by year")
    region: str | None = Field(None, description="Filter by region")
    top_k: int = Field(5, description="Number of results", ge=1, le=50)


# ──────────────────────────────────────────────
# 📤 RESPONSE MODELS
# ──────────────────────────────────────────────

class SourceResponse(BaseModel):
    """One source citation in a RAG response."""
    source_id: int
    company: str
    year: str
    region: str
    relevance_score: float
    chunk_preview: str


class AskResponse(BaseModel):
    """Response from the /api/ask endpoint."""
    answer: str
    query: str
    sources: list[SourceResponse]
    retrieval_time: float
    generation_time: float
    total_time: float
    chunks_searched: int


class SearchResultResponse(BaseModel):
    """One search result."""
    text: str
    score: float
    company: str
    year: str
    region: str
    chunk_index: int


class SearchResponse(BaseModel):
    """Response from the /api/search endpoint."""
    query: str
    results: list[SearchResultResponse]
    total_results: int


class DocumentResponse(BaseModel):
    """One document in the list."""
    id: int
    file_name: str
    company: str
    year: str
    region: str
    total_chunks: int
    report_type: str


class UploadResponse(BaseModel):
    """Response from the /api/upload endpoint."""
    message: str
    file_name: str
    chunks_created: int
    document_id: int


class HealthResponse(BaseModel):
    """Response from the /api/health endpoint."""
    status: str
    app_name: str
    total_documents: int
    total_chunks: int

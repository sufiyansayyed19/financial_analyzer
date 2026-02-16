"""
🧠 FinRAG — Database Models
==============================

WHAT THIS DOES:
---------------
Defines the STRUCTURE of our database tables using SQLAlchemy ORM.

WHY ORM (Object-Relational Mapping)?
--------------------------------------
Without ORM:
  cursor.execute("INSERT INTO chunks (text, company) VALUES (?, ?)", (text, company))
  → Raw strings, no type checking, easy to make typos

With ORM:
  chunk = Chunk(text=text, company=company)
  session.add(chunk)
  → Python objects, IDE autocomplete, type safety

ORM translates Python objects ↔ database rows automatically.

TABLE RELATIONSHIPS:
─────────────────────
A Document HAS MANY Chunks.
A Document HAS MANY Tables.

  Document (1) ──→ (many) Chunk
  Document (1) ──→ (many) ExtractedTable

This is a "one-to-many" relationship, enforced by foreign keys.
If a document is deleted, its chunks and tables are too (CASCADE).

WHAT YOU'LL LEARN:
- SQLAlchemy ORM model definitions
- Column types (String, Text, Integer, LargeBinary)
- Relationships and foreign keys
- Storing binary data (embeddings) in the database
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from backend.db.database import Base


class Document(Base):
    """
    A financial document (one PDF = one row).

    WHY A SEPARATE TABLE?
    Instead of repeating company/year/region in every chunk row,
    we store it ONCE in the document table and reference it.
    This is database normalization — avoids data duplication.

    Example row:
        id=1, company="nvidia", year="2024", file_name="nvidia_2024_annual.pdf"
    """

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False, unique=True)
    company = Column(String(100), nullable=False, index=True)
    year = Column(String(10), nullable=False, index=True)
    region = Column(String(50), nullable=False, index=True)
    report_type = Column(String(50), default="annual")
    total_pages = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # ── Relationships ──
    # This tells SQLAlchemy: "a document has many chunks"
    # back_populates creates a two-way link:
    #   doc.chunks → list of chunks
    #   chunk.document → the parent document
    chunks = relationship(
        "Chunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Document {self.company}/{self.year} ({self.total_chunks} chunks)>"


class Chunk(Base):
    """
    A text chunk with its embedding vector.

    This is the CORE table for RAG — each row contains:
    1. The text content (what the LLM will read)
    2. The embedding vector (what search uses to find relevant chunks)
    3. Metadata (company, year — for filtering)

    WHY STORE EMBEDDINGS AS BINARY (LargeBinary)?
    ────────────────────────────────────────────────
    Embeddings are numpy arrays (384 floats = 1,536 bytes).
    Options:
    1. JSON array → 3-4KB per row, slow to parse
    2. Binary blob → 1.5KB per row, fast to load with np.frombuffer()
    3. pgvector type → native PostgreSQL vector ops (Phase 5)

    We use binary for now — compact and fast.
    When we migrate to PostgreSQL, we'll add pgvector for native search.
    """

    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)  # Position in document
    text = Column(Text, nullable=False)

    # ── Embedding (binary blob) ──
    # Stored as raw bytes: numpy array → .tobytes() → LargeBinary
    # Loaded back: np.frombuffer(blob, dtype=np.float32)
    embedding = Column(LargeBinary, nullable=True)  # Nullable until we embed

    # ── Metadata (denormalized for fast filtering) ──
    # YES, this duplicates data from the Document table.
    # WHY? Because search queries filter by company/year.
    # Joining tables on every search query is slow.
    # Denormalization trades storage for speed — standard in search systems.
    company = Column(String(100), nullable=False, index=True)
    year = Column(String(10), nullable=False, index=True)
    region = Column(String(50), nullable=False, index=True)

    # ── Chunk stats ──
    char_count = Column(Integer, default=0)

    # ── Relationship ──
    document = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<Chunk {self.company}/{self.year} #{self.chunk_index} ({self.char_count} chars)>"


# ──────────────────────────────────────────────
# 🧪 TEST: Run directly to verify models
# ──────────────────────────────────────────────
if __name__ == "__main__":
    from backend.db.database import init_db, get_session

    print("\n" + "=" * 60)
    print("🧪 DATABASE MODELS TEST")
    print("=" * 60)

    # Create tables
    init_db()

    # Test creating objects
    session = get_session()

    doc = Document(
        file_name="test_2024_annual.pdf",
        company="test",
        year="2024",
        region="us",
        total_pages=10,
        total_chunks=5,
    )
    session.add(doc)
    session.commit()

    print(f"\n✅ Created: {doc}")
    print(f"   ID: {doc.id}")

    # Clean up test data
    session.delete(doc)
    session.commit()
    session.close()

    print("   Test data cleaned up")
    print("   Models are working correctly!")

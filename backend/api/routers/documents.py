"""
🧠 FinRAG — Document Router
==============================

ENDPOINTS:
  POST   /api/upload          → Upload + process a PDF
  GET    /api/documents       → List all stored documents
  DELETE /api/documents/{id}  → Remove a document

WHAT YOU'LL LEARN:
- FastAPI file upload handling
- Running background pipelines from API endpoints
- Database CRUD operations via API
- HTTP status codes (201 Created, 404 Not Found)
"""

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, status

from backend.api.schemas import DocumentResponse, UploadResponse
from backend.core.config import settings
from backend.core.logging import get_logger
from backend.db.database import get_session, init_db
from backend.db.models import Chunk, Document

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


# ──────────────────────────────────────────────
# 📤 UPLOAD PDF
# ──────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a PDF",
)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a financial PDF → extract → clean → chunk → embed → store.

    This runs the ENTIRE pipeline from Phase 1 + Phase 2:
    1. Save uploaded PDF to data directory
    2. Extract text (PyMuPDF)
    3. Clean text (10-step pipeline)
    4. Chunk text (smart chunking)
    5. Generate embeddings (all-MiniLM-L6-v2)
    6. Store in database

    The file must be a PDF. Processing takes ~30-60 seconds per document.
    """
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted"
        )

    # Check if already processed
    session = get_session()
    try:
        existing = session.query(Document).filter_by(
            file_name=file.filename
        ).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Document '{file.filename}' already exists (ID: {existing.id})"
            )
    finally:
        session.close()

    # Save uploaded file to temp location
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)

        logger.info(f"📥 Uploaded: {file.filename} → {tmp_path}")

        # Run the full ingestion pipeline
        from backend.pipelines.pdf_extractor import extract_pdf
        from backend.pipelines.text_cleaner import clean_text
        from backend.pipelines.chunking_engine import chunk_text
        from backend.engines.embedder import embed_batch
        import numpy as np

        # Step 1: Extract text
        raw_text = extract_pdf(str(tmp_path))
        if not raw_text or len(raw_text.strip()) < 50:
            raise HTTPException(
                status_code=422,
                detail="Could not extract meaningful text from this PDF"
            )

        # Step 2: Clean text
        cleaned_text = clean_text(raw_text)

        # Step 3: Chunk text
        chunks = chunk_text(cleaned_text)
        if not chunks:
            raise HTTPException(
                status_code=422,
                detail="No chunks could be created from this PDF"
            )

        # Step 4: Generate embeddings
        chunk_texts = [c["text"] for c in chunks]
        embeddings = embed_batch(chunk_texts, show_progress=False)

        # Step 5: Parse metadata from filename
        # Expected: company_year_type.pdf (e.g., nvidia_2024_annual.pdf)
        name_parts = file.filename.replace(".pdf", "").split("_")
        company = name_parts[0].lower() if len(name_parts) > 0 else "unknown"
        year = "unknown"
        for part in name_parts:
            if part.isdigit() and len(part) == 4:
                year = part
                break
        region = "unknown"

        # Step 6: Store in database
        init_db()
        session = get_session()
        try:
            doc = Document(
                file_name=file.filename,
                company=company,
                year=year,
                region=region,
                report_type="annual",
                total_chunks=len(chunks),
            )
            session.add(doc)
            session.flush()

            chunk_objects = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_obj = Chunk(
                    document_id=doc.id,
                    chunk_index=chunk.get("chunk_index", i),
                    text=chunk["text"],
                    embedding=embedding.astype(np.float32).tobytes(),
                    company=company,
                    year=year,
                    region=region,
                    char_count=len(chunk["text"]),
                )
                chunk_objects.append(chunk_obj)

            session.bulk_save_objects(chunk_objects)
            session.commit()

            logger.info(f"✅ Stored {len(chunk_objects)} chunks for {file.filename}")

            return UploadResponse(
                message=f"Successfully processed {file.filename}",
                file_name=file.filename,
                chunks_created=len(chunk_objects),
                document_id=doc.id,
            )

        except Exception as e:
            session.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            session.close()

    finally:
        # Clean up temp file
        if tmp_path.exists():
            tmp_path.unlink()


# ──────────────────────────────────────────────
# 📋 LIST DOCUMENTS
# ──────────────────────────────────────────────

@router.get(
    "/documents",
    response_model=list[DocumentResponse],
    summary="List all stored documents",
)
async def list_documents():
    """Return all documents currently in the database."""
    session = get_session()
    try:
        docs = session.query(Document).order_by(Document.company, Document.year).all()
        return [
            DocumentResponse(
                id=doc.id,
                file_name=doc.file_name,
                company=doc.company,
                year=doc.year,
                region=doc.region,
                total_chunks=doc.total_chunks,
                report_type=doc.report_type or "annual",
            )
            for doc in docs
        ]
    finally:
        session.close()


# ──────────────────────────────────────────────
# 🗑️ DELETE DOCUMENT
# ──────────────────────────────────────────────

@router.delete(
    "/documents/{document_id}",
    summary="Delete a document and all its chunks",
)
async def delete_document(document_id: int):
    """
    Remove a document and all associated chunks from the database.

    This is a CASCADE delete — removing the document
    automatically removes all its chunks.
    """
    session = get_session()
    try:
        doc = session.query(Document).filter_by(id=document_id).first()
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"Document with ID {document_id} not found"
            )

        file_name = doc.file_name
        chunk_count = doc.total_chunks
        session.delete(doc)
        session.commit()

        logger.info(f"🗑️ Deleted: {file_name} ({chunk_count} chunks)")

        return {
            "message": f"Deleted {file_name}",
            "chunks_removed": chunk_count,
        }
    finally:
        session.close()

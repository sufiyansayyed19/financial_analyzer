"""
🧠 FinRAG — Application Entry Point
=====================================

This is where FastAPI will live (Phase 5).
For now, it serves as a quick validation that our project structure works.

Run with:
    cd "d:\\New folder\\nlp_project"
    venv\\Scripts\\python -m backend.main
"""

from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


def main() -> None:
    """Quick health check — validates project structure is working."""
    logger.info(f"🚀 {settings.app_name} initialized!")
    logger.info(f"📂 Data directory:      {settings.data_dir}")
    logger.info(f"📂 Processed directory:  {settings.processed_dir}")
    logger.info(f"📄 Debug mode:           {settings.debug}")
    logger.info(f"🔧 Chunk size:           {settings.chunk_size} chars")
    logger.info(f"🔧 Chunk overlap:        {settings.chunk_overlap} chars")

    # Validate directories exist
    if settings.data_dir.exists():
        pdf_count = len(list(settings.data_dir.rglob("*.pdf")))
        logger.info(f"✅ Found {pdf_count} PDFs in data directory")
    else:
        logger.warning(f"⚠️  Data directory not found: {settings.data_dir}")

    if not settings.processed_dir.exists():
        settings.processed_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Created processed directory: {settings.processed_dir}")

    logger.info("✅ Project structure validated successfully!")


if __name__ == "__main__":
    main()

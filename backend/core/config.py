"""
🧠 FinRAG — Core Configuration
================================

WHY THIS FILE EXISTS:
---------------------
Every production app needs a SINGLE place to manage settings.
Without this, you'd have hardcoded paths and values scattered everywhere.

HOW IT WORKS:
-------------
We use Pydantic's BaseSettings which:
1. Reads from a .env file (so secrets never go in code)
2. Validates types automatically
3. Gives us autocomplete and type safety

WHAT YOU'LL LEARN:
- Pydantic BaseSettings pattern
- Environment variable management
- Path handling with pathlib
"""

from pathlib import Path

from pydantic_settings import BaseSettings


# ──────────────────────────────────────────────
# 🏗 PROJECT PATHS
# ──────────────────────────────────────────────
# We compute paths relative to the project root.
# __file__ = this file's path (backend/core/config.py)
# .parent  = backend/core/
# .parent  = backend/
# .parent  = nlp_project/ (the project root)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Central configuration for the entire FinRAG application.

    Values are loaded from .env file → environment variables → defaults.
    Priority: env var > .env file > default value here.
    """

    # ── Application ──
    app_name: str = "FinRAG"
    debug: bool = True

    # ── Paths ──
    # Where raw PDFs are stored
    data_dir: Path = PROJECT_ROOT / "data"
    # Where processed output goes
    processed_dir: Path = PROJECT_ROOT / "processed"

    # ── PDF Processing ──
    # How many characters per chunk (we'll tune this later)
    chunk_size: int = 1000
    # Overlap between chunks to preserve context across boundaries
    chunk_overlap: int = 200

    # ── Logging ──
    log_level: str = "INFO"

    model_config = {
        # This tells Pydantic to also read from a .env file
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        # Allow extra fields from .env without crashing
        "extra": "ignore",
    }


# ──────────────────────────────────────────────
# 🎯 SINGLETON PATTERN
# ──────────────────────────────────────────────
# We create ONE settings instance that the whole app imports.
# This avoids reading .env multiple times and ensures consistency.
#
# Usage anywhere in the project:
#   from backend.core.config import settings
#   print(settings.data_dir)

settings = Settings()

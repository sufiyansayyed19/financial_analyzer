"""
🧠 FinRAG — Structured Logging
================================

WHY STRUCTURED LOGGING:
-----------------------
In production, you don't read logs line by line.
You SEARCH them. Structured logs let you filter by:
- document_id, step_name, company, status, etc.

Without this, debugging a failed ingestion across 21 PDFs
would be like finding a needle in a haystack.

WHAT WE USE:
- Python's built-in `logging` module (standard, works everywhere)
- `rich` library for beautiful terminal output during development

WHAT YOU'LL LEARN:
- Setting up a reusable logger
- Why structured logging matters in real systems
"""

import logging
import sys

from rich.logging import RichHandler

from backend.core.config import settings


def get_logger(name: str) -> logging.Logger:
    """
    Create a named logger with consistent formatting.

    Usage:
        from backend.core.logging import get_logger
        logger = get_logger(__name__)

        logger.info("Processing document", extra={"document_id": "nvidia_2024"})
        logger.error("Extraction failed", extra={"page": 42, "error": "garbled text"})

    WHY pass __name__?
    → It automatically sets the logger name to the module path,
      e.g., "backend.pipelines.pdf_extractor"
      So you know EXACTLY where each log came from.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if called multiple times
    if not logger.handlers:
        # Rich handler gives us colored, formatted terminal output
        handler = RichHandler(
            rich_tracebacks=True,       # Pretty stack traces
            show_time=True,
            show_path=True,             # Shows file path in logs
            markup=False,               # Disabled to avoid PowerShell piping issues
        )

        # Format: [TIME] [LEVEL] [MODULE] message
        formatter = logging.Formatter(
            "%(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Set level from config
        logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    return logger

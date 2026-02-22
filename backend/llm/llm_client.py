"""
🧠 FinRAG — LLM Client
=========================

WHAT THIS DOES:
---------------
Provides a clean interface to talk to LLMs (Large Language Models).
Currently supports Google Gemini. Built with abstraction so adding
OpenAI or any other provider is just a new class.

WHY ABSTRACTION?
-----------------
We DON'T want LLM-specific code scattered through the project.
By using a base class + implementations, the rest of the app just calls:
    response = client.generate(prompt)
Without caring whether it's Gemini, GPT, or a local model.

DESIGN PATTERN: Strategy Pattern
─────────────────────────────────
                    BaseLLMClient (interface)
                    /                  \\
            GeminiClient          OpenAIClient (future)
               |                       |
         calls Gemini API         calls OpenAI API

The rag_pipeline.py only knows about BaseLLMClient.
Switching providers = changing one config variable.

WHAT YOU'LL LEARN:
- Abstract base classes in Python
- API client patterns
- Strategy pattern for extensibility
- Error handling for external services
"""

import time
from abc import ABC, abstractmethod

import google.generativeai as genai

from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────
# 🏗 ABSTRACT BASE CLASS
# ──────────────────────────────────────────────
# This defines WHAT any LLM client must do,
# without specifying HOW (that's up to each implementation).

class BaseLLMClient(ABC):
    """
    Abstract base for all LLM clients.

    WHY ABSTRACT?
    Any new LLM provider (OpenAI, Anthropic, local) just needs to:
    1. Inherit from BaseLLMClient
    2. Implement generate()
    That's it. The rest of the app doesn't change.
    """

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt (includes context + question)
            system_prompt: Instructions for the LLM's behavior

        Returns:
            The LLM's text response
        """
        pass


# ──────────────────────────────────────────────
# 🤖 GEMINI IMPLEMENTATION
# ──────────────────────────────────────────────

class GeminiClient(BaseLLMClient):
    """
    Google Gemini API client.

    Uses the google-generativeai SDK.
    Free tier: 1,500 requests/day — plenty for development.
    """

    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY not set! "
                "Get a free key at: https://aistudio.google.com/apikey "
                "Then add it to your .env file."
            )

        genai.configure(api_key=settings.gemini_api_key)

        self.model = genai.GenerativeModel(
            model_name=settings.llm_model,
            generation_config=genai.GenerationConfig(
                temperature=settings.llm_temperature,
                max_output_tokens=settings.llm_max_tokens,
            ),
        )
        logger.info(
            f"✅ Gemini client initialized "
            f"(model={settings.llm_model}, temp={settings.llm_temperature})"
        )

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Send a prompt to Gemini and get a response.

        HOW GEMINI API WORKS:
        1. We send a prompt (text) to the API
        2. The model processes it (~1-3 seconds)
        3. We get back generated text

        System prompt is prepended to set the LLM's "role/behavior".

        RETRY LOGIC: Free tier has per-minute rate limits.
        If we hit a 429, we wait and retry (up to 3 times).
        """
        # Combine system prompt + user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        max_retries = 3
        retry_delay = 5  # seconds

        for attempt in range(max_retries):
            start = time.time()
            try:
                response = self.model.generate_content(full_prompt)
                elapsed = time.time() - start

                if response.text:
                    logger.info(f"🤖 Gemini responded in {elapsed:.1f}s ({len(response.text)} chars)")
                    return response.text.strip()
                else:
                    logger.warning("Gemini returned empty response")
                    return "I couldn't generate a response. Please try rephrasing your question."

            except Exception as e:
                elapsed = time.time() - start
                error_str = str(e)

                # Rate limit error — retry after delay
                if "429" in error_str or "quota" in error_str.lower() or "resource" in error_str.lower():
                    if attempt < max_retries - 1:
                        wait = retry_delay * (attempt + 1)
                        logger.warning(
                            f"⏳ Rate limited (attempt {attempt+1}/{max_retries}), "
                            f"retrying in {wait}s..."
                        )
                        time.sleep(wait)
                        continue

                logger.error(f"❌ Gemini API error ({elapsed:.1f}s): {e}")
                return f"Error communicating with the LLM: {error_str}"

        return "Rate limit exceeded after retries. Please wait a moment and try again."


# ──────────────────────────────────────────────
# 🏭 CLIENT FACTORY
# ──────────────────────────────────────────────
# Creates the right client based on config.
# This is the only function the rest of the app calls.

_client: BaseLLMClient | None = None


def get_llm_client() -> BaseLLMClient:
    """
    Get the LLM client (lazy singleton).

    Uses settings.llm_provider to decide which client to create.
    Currently supports: "gemini"
    """
    global _client
    if _client is None:
        provider = settings.llm_provider.lower()

        if provider == "gemini":
            _client = GeminiClient()
        else:
            raise ValueError(
                f"Unknown LLM provider: '{provider}'. "
                f"Supported: 'gemini'"
            )

    return _client


# ──────────────────────────────────────────────
# 🧪 TEST: Run directly to verify Gemini works
# ──────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 LLM CLIENT TEST")
    print("=" * 60)

    client = get_llm_client()
    response = client.generate(
        "What is Retrieval-Augmented Generation (RAG) in 2 sentences?"
    )
    print(f"\n🤖 Response:\n{response}")

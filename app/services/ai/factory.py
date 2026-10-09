from typing import Optional

from app.core.config import settings
from app.services.ai.base import AIProvider
from app.services.ai.providers import OpenAICompatibleProvider

# Default endpoint untuk provider yang populer (OpenAI-compatible)
_DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "ollama": "http://localhost:11434/v1",
    "azure": None,  # Azure wajib mengisi AI_BASE_URL sendiri
    "opencode": "https://opencode.ai/zen/v1",
    "opencode-go": "https://opencode.ai/zen/v1",
}


def get_ai_provider() -> Optional[AIProvider]:
    """
    Factory untuk mendapatkan provider LLM sesuai config.

    Returns:
        Instance AIProvider jika AI_ENABLED=True dan provider valid;
        None jika AI dinonaktifkan.
    """
    if not settings.AI_ENABLED or settings.AI_PROVIDER.lower() == "none":
        return None

    provider = settings.AI_PROVIDER.lower()
    base_url = settings.AI_BASE_URL or _DEFAULT_BASE_URLS.get(provider)

    if not base_url:
        raise ValueError(
            f"AI_BASE_URL wajib diisi untuk provider '{provider}'"
        )

    return OpenAICompatibleProvider(
        base_url=base_url,
        api_key=settings.AI_API_KEY or "",
        model=settings.AI_MODEL,
        timeout=settings.AI_TIMEOUT,
        max_retries=settings.AI_MAX_RETRIES,
    )

import asyncio
import json
import logging
import random
from typing import Type

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.services.ai.base import AIError, AIProvider

logger = logging.getLogger(__name__)

# Status HTTP yang layak di-retry (transient / rate limit)
_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


def _strip_code_fence(content: str) -> str:
    """Buang wrapper ```json ... ``` yang kadang dikeluarkan model."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    return content


def _backoff(attempt: int) -> float:
    """Exponential backoff + jitter (detik)."""
    delay = min(
        settings.AI_RETRY_BASE * (2 ** attempt),
        settings.AI_RETRY_MAX,
    )
    return delay + random.uniform(0, settings.AI_RETRY_JITTER)


class OpenAICompatibleProvider(AIProvider):
    """
    Provider LLM via endpoint OpenAI-compatible.

    Mendukung OpenAI, Azure OpenAI, Google AI Studio (Gemini endpoint
    /v1beta/openai/), OpenCode Zen (/v1), dan Ollama lokal (/v1) hanya
    dengan mengganti base_url, api_key, dan model.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: int = 60,
        max_retries: int = 2,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    async def complete_json(
        self, system: str, user: str, schema: Type[BaseModel]
    ) -> BaseModel:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        base_body = {
            "model": self.model,
            "messages": messages,
            "temperature": settings.AI_TEMPERATURE,
        }

        use_response_format = True
        max_attempts = self.max_retries + 1
        last_error: Exception | None = None

        def _raise_final() -> None:
            msg = f"AI request failed after {max_attempts} attempts: {last_error}"
            if isinstance(last_error, httpx.HTTPStatusError) and last_error.response is not None:
                msg += f" | body: {last_error.response.text[:300]}"
            raise AIError(msg) from last_error

        for attempt in range(max_attempts):
            body = dict(base_body)
            if use_response_format:
                body["response_format"] = {"type": "json_object"}

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=body,
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(_strip_code_fence(content))
                    return schema.model_validate(parsed)

            except httpx.HTTPStatusError as exc:
                last_error = exc
                status = exc.response.status_code
                body_text = exc.response.text[:300]

                # 400 karena response_format tidak didukung → coba sekali tanpa itu
                if status == 400 and use_response_format:
                    logger.info(
                        "response_format ditolak (HTTP 400), retry tanpa response_format"
                    )
                    use_response_format = False
                    continue

                if status not in _RETRYABLE_STATUS:
                    raise AIError(
                        f"AI request failed (HTTP {status}) for model "
                        f"'{self.model}': {exc} | body: {body_text}"
                    ) from exc

            except (httpx.TransportError, json.JSONDecodeError, KeyError, ValidationError) as exc:
                last_error = exc

            if attempt < max_attempts - 1:
                delay = _backoff(attempt)
                logger.warning(
                    "AI request attempt %d/%d failed (%s); retry in %.1fs",
                    attempt + 1,
                    max_attempts,
                    last_error,
                    delay,
                )
                await asyncio.sleep(delay)

        _raise_final()
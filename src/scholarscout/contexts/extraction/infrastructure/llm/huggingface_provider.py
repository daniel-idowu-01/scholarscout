"""
Hugging Face provider for opportunity extraction.

Uses the HF Inference Providers router (https://router.huggingface.co/v1),
which exposes an OpenAI-compatible chat-completions API over open models.
A free Hugging Face account token (https://huggingface.co/settings/tokens)
includes a small monthly credit allowance — enough for development.

Default model: Qwen/Qwen2.5-7B-Instruct (ungated — works with any HF token)
  → cheap, fast, good enough for structured JSON extraction
"""

from __future__ import annotations

import logging

import httpx

from scholarscout.config import settings
from scholarscout.contexts.extraction.infrastructure.llm.base import (
    EXTRACTION_SYSTEM_PROMPT,
    LLMProvider,
    LLMResponse,
)

logger = logging.getLogger(__name__)

_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"


class HuggingFaceProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or settings.llm.huggingface_api_key
        self._model = model or settings.llm.huggingface_default_model

    async def extract(self, markdown: str, url: str) -> LLMResponse:
        truncated = self._truncate_markdown(markdown)

        user_message = (
            f"URL: {url}\n\n"
            f"Page content:\n\n{truncated}\n\n"
            "Extract all graduate funding opportunities from this page. "
            "Return only valid JSON."
        )

        payload = {
            "model": self._model,
            "max_tokens": settings.llm.max_tokens_per_call,
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    _ROUTER_URL,
                    json=payload,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "HuggingFace API error %s: %s", e.response.status_code, e.response.text[:500]
            )
            return self._error_response(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
        except (httpx.HTTPError, ValueError) as e:
            logger.error("HuggingFace request failed: %s", e)
            return self._error_response(str(e))

        try:
            raw_text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            logger.error("Unexpected HuggingFace response shape: %s", e)
            return self._error_response(f"unexpected response shape: {e}")

        usage = data.get("usage") or {}
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        result = LLMResponse(
            raw_text=raw_text,
            parsed_json=self._parse_json_response(raw_text),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self._model,
            provider="huggingface",
            cost_usd=self.estimate_cost(input_tokens, output_tokens),
        )
        self._record_metrics(result)
        return result

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # Pricing varies per HF inference provider; this is a rough upper bound
        # for small open models (~$0.10/M in, ~$0.30/M out).
        return (input_tokens * 0.10 + output_tokens * 0.30) / 1_000_000

    def _error_response(self, error: str) -> LLMResponse:
        return LLMResponse(
            raw_text="",
            parsed_json=None,
            input_tokens=0,
            output_tokens=0,
            model=self._model,
            provider="huggingface",
            error=error,
        )

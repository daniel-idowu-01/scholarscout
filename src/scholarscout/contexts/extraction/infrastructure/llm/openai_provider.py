"""
OpenAI provider for opportunity extraction.

Used as fallback when Anthropic is unavailable, or as primary
when configured via LLM_DEFAULT_PROVIDER=openai.
"""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from scholarscout.config import settings
from scholarscout.contexts.extraction.infrastructure.llm.base import (
    EXTRACTION_SYSTEM_PROMPT,
    LLMProvider,
    LLMResponse,
)

logger = logging.getLogger(__name__)

_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
}


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key or settings.llm.openai_api_key)
        self._model = model or settings.llm.openai_default_model

    async def extract(self, markdown: str, url: str) -> LLMResponse:
        truncated = self._truncate_markdown(markdown)

        user_message = (
            f"URL: {url}\n\n"
            f"Page content:\n\n{truncated}\n\n"
            "Extract all graduate funding opportunities. Return only valid JSON."
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=settings.llm.max_tokens_per_call,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            return LLMResponse(
                raw_text="",
                parsed_json=None,
                input_tokens=0,
                output_tokens=0,
                model=self._model,
                provider="openai",
                error=str(e),
            )

        raw_text = response.choices[0].message.content or ""
        parsed = self._parse_json_response(raw_text)
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0
        cost = self.estimate_cost(input_tokens, output_tokens)

        result = LLMResponse(
            raw_text=raw_text,
            parsed_json=parsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self._model,
            provider="openai",
            cost_usd=cost,
        )
        self._record_metrics(result)
        return result

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        pricing = _PRICING.get(self._model, {"input": 2.5, "output": 10.0})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

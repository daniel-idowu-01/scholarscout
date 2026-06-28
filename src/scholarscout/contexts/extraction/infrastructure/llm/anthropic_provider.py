"""
Anthropic Claude provider for opportunity extraction.

Default extraction model: claude-haiku-4-5-20251001
  → Fast, cheap, accurate for structured extraction tasks
High-accuracy model: claude-sonnet-4-6
  → Used for complex/ambiguous pages with low confidence

Pricing (as of 2025):
  haiku-4-5:   $0.80/M input, $4.00/M output
  sonnet-4-6:  $3.00/M input, $15.00/M output
"""

from __future__ import annotations

import logging

import anthropic

from scholarscout.config import settings
from scholarscout.contexts.extraction.infrastructure.llm.base import (
    EXTRACTION_SYSTEM_PROMPT,
    LLMProvider,
    LLMResponse,
)

logger = logging.getLogger(__name__)

# Pricing per million tokens (as of 2025-Q4)
_PRICING: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-8": {"input": 15.00, "output": 75.00},
}


class AnthropicProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key or settings.llm.anthropic_api_key
        )
        self._model = model or settings.llm.anthropic_default_model

    async def extract(self, markdown: str, url: str) -> LLMResponse:
        truncated = self._truncate_markdown(markdown)

        user_message = (
            f"URL: {url}\n\n"
            f"Page content:\n\n{truncated}\n\n"
            "Extract all graduate funding opportunities from this page. "
            "Return only valid JSON."
        )

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=settings.llm.max_tokens_per_call,
                system=EXTRACTION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
        except anthropic.APIError as e:
            logger.error("Anthropic API error: %s", e)
            return LLMResponse(
                raw_text="",
                parsed_json=None,
                input_tokens=0,
                output_tokens=0,
                model=self._model,
                provider="anthropic",
                error=str(e),
            )

        raw_text = response.content[0].text if response.content else ""
        parsed = self._parse_json_response(raw_text)
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = self.estimate_cost(input_tokens, output_tokens)

        result = LLMResponse(
            raw_text=raw_text,
            parsed_json=parsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self._model,
            provider="anthropic",
            cost_usd=cost,
        )
        self._record_metrics(result)
        return result

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        pricing = _PRICING.get(self._model, {"input": 3.0, "output": 15.0})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

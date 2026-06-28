"""
LLM Provider abstraction.

Why abstract the LLM:
- Provider pricing changes (switch cheaply)
- Cost control: route simple extractions to cheaper models
- Fallback: if Anthropic is down, try OpenAI
- Local models for development / cost-zero offline testing

Token budget per extraction:
  Input: ~3,000 tokens (truncated markdown)
  Output: ~500 tokens (structured JSON)
  ~$0.0005 per page on claude-haiku-4-5 at current pricing.
  At 100k pages/day → ~$50/day. Monthly budget gate enforced.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from scholarscout.shared.infrastructure.telemetry.metrics import (
    llm_cost_usd_total,
    llm_tokens_used_total,
)

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """\
You are an expert at extracting graduate scholarship and funding information from university web pages.

Extract ALL scholarship, fellowship, assistantship, studentship, and funded graduate program opportunities mentioned on the page.

For each opportunity, extract:
- title: The name of the opportunity
- degree_level: one of [phd, masters, postdoc, any, undergraduate]
- funding_type: one of [fully_funded, partial, tuition_only, stipend_only, unknown]
- stipend_amount: annual stipend in USD if mentioned (null if not)
- stipend_currency: currency if mentioned (e.g., USD, EUR, GBP)
- tuition_covered: true/false/null
- application_fee: amount in USD if mentioned
- deadline: application deadline in ISO 8601 format (null if not found)
- departments: list of relevant departments/fields
- description: 2-3 sentence summary
- requirements: key eligibility requirements as a list
- citizenship_restrictions: list of eligible nationalities/citizenships (null if open to all)
- gpa_minimum: minimum GPA if specified
- language_requirements: e.g., {"IELTS": "6.5", "TOEFL": "90"}
- duration_years: program length in years if mentioned
- url: the URL of the page if mentioned in the content

Return a JSON object with key "opportunities" containing a list of opportunity objects.
If no opportunities are found, return {"opportunities": []}.
Be conservative: only extract what is clearly stated. Do not hallucinate values.
"""


@dataclass
class LLMResponse:
    raw_text: str
    parsed_json: dict[str, Any] | None
    input_tokens: int
    output_tokens: int
    model: str
    provider: str
    cost_usd: float = 0.0
    error: str | None = None


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @abstractmethod
    async def extract(self, markdown: str, url: str) -> LLMResponse:
        """Extract opportunities from markdown content."""
        raise NotImplementedError

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD for a given number of tokens."""
        raise NotImplementedError

    def _record_metrics(self, response: LLMResponse) -> None:
        llm_tokens_used_total.labels(
            provider=response.provider, model=response.model, direction="input"
        ).inc(response.input_tokens)
        llm_tokens_used_total.labels(
            provider=response.provider, model=response.model, direction="output"
        ).inc(response.output_tokens)
        llm_cost_usd_total.labels(
            provider=response.provider, model=response.model
        ).inc(response.cost_usd)

    @staticmethod
    def _truncate_markdown(markdown: str, max_chars: int = 12_000) -> str:
        """Truncate to avoid excessive token usage while keeping context."""
        if len(markdown) <= max_chars:
            return markdown
        # Keep first 80% and last 20% — head has titles, tail has deadlines
        head = int(max_chars * 0.8)
        tail = max_chars - head
        return markdown[:head] + "\n\n[...content truncated...]\n\n" + markdown[-tail:]

    @staticmethod
    def _parse_json_response(text: str) -> dict[str, Any] | None:
        """Robustly parse JSON from LLM output — handles markdown code blocks."""
        # Strip markdown code fences
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object within the text
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

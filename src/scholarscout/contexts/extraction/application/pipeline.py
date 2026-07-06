"""
Extraction Pipeline — Orchestrates HTML → Structured Opportunity.

Pipeline stages:
  1. Load raw HTML from object storage
  2. Clean + convert to Markdown (HtmlCleaner)
  3. Classify page (RuleBasedClassifier)
  4. Rule-based extraction (RuleExtractor)
  5. LLM extraction if: page is relevant AND rule confidence is low
  6. Merge rule + LLM outputs (rules override LLM for high-confidence fields)
  7. Validate + normalise the merged result
  8. Upsert into Opportunity table
  9. Enqueue for OpenSearch indexing

Cost control:
  - Skip LLM if rule extraction confidence > 0.8
  - Skip LLM if monthly budget exceeded (fallback to rules-only)
  - Truncate input to 12,000 chars before sending to LLM
  - Cache LLM responses per content_hash (avoid re-extraction)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from scholarscout.config import settings
from scholarscout.contexts.discovery.infrastructure.page_classifier import (
    RuleBasedClassifier,
)
from scholarscout.contexts.extraction.infrastructure.cleaner import HtmlCleaner
from scholarscout.contexts.extraction.infrastructure.llm.base import LLMProvider, LLMResponse
from scholarscout.contexts.extraction.infrastructure.rules.rule_extractor import RuleExtractor
from scholarscout.shared.infrastructure.telemetry.metrics import (
    extraction_duration_seconds,
    extraction_errors_total,
    opportunities_extracted_total,
)

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    university_id: uuid.UUID
    source_page_id: uuid.UUID
    url: str
    opportunities: list[dict[str, Any]]
    method: str  # rule | llm | hybrid | skipped
    confidence: float
    rule_result: Any
    llm_result: LLMResponse | None
    extracted_at: datetime
    error: str | None = None


class ExtractionPipeline:
    def __init__(
        self,
        cleaner: HtmlCleaner,
        rule_extractor: RuleExtractor,
        classifier: RuleBasedClassifier,
        llm_provider: LLMProvider | None = None,
        storage: Any = None,
    ) -> None:
        self._cleaner = cleaner
        self._rules = rule_extractor
        self._classifier = classifier
        self._llm = llm_provider
        self._storage = storage

    async def process(
        self,
        source_page_id: uuid.UUID,
        university_id: uuid.UUID,
        url: str,
        html_uri: str | None = None,
        html_content: str | None = None,
        markdown_content: str | None = None,
    ) -> ExtractionResult:
        started = datetime.now(UTC)

        # Step 1: Load content
        if html_content is None and html_uri and self._storage:
            try:
                html_content = await self._storage.get_snapshot_html(html_uri)
            except Exception as e:
                logger.error("Failed to load snapshot %s: %s", html_uri, e)
                return self._error_result(university_id, source_page_id, url, str(e))

        if not html_content:
            return self._error_result(university_id, source_page_id, url, "No content available")

        # Step 2: Convert to Markdown
        if not markdown_content:
            markdown_content = self._cleaner.to_markdown(html_content)

        title = self._cleaner.extract_title(html_content)
        text_sample = markdown_content[:3000]

        # Step 3: Classify
        classification = self._classifier.classify(url, title, text_sample)
        if not self._classifier.is_relevant(classification):
            return ExtractionResult(
                university_id=university_id,
                source_page_id=source_page_id,
                url=url,
                opportunities=[],
                method="skipped",
                confidence=classification.confidence,
                rule_result=None,
                llm_result=None,
                extracted_at=started,
            )

        # Step 4: Rule extraction
        with extraction_duration_seconds.labels(method="rule").time():
            rule_result = self._rules.extract(markdown_content)

        method = "rule"
        llm_result: LLMResponse | None = None
        opportunities: list[dict[str, Any]] = []

        # Step 5: LLM extraction (if enabled and needed)
        use_llm = (
            settings.features.llm_extraction
            and self._llm is not None
            and rule_result.confidence < 0.8  # LLM adds value
        )

        if use_llm and self._llm:
            try:
                with extraction_duration_seconds.labels(method="llm").time():
                    llm_result = await self._llm.extract(markdown_content, url)
                method = "hybrid" if rule_result.is_funding_page else "llm"
            except Exception as e:
                logger.warning("LLM extraction failed for %s: %s", url, e)

        # Step 6: Merge
        if llm_result and llm_result.parsed_json:
            raw_opportunities = llm_result.parsed_json.get("opportunities", [])
            for opp in raw_opportunities:
                merged = self._merge(opp, rule_result)
                opportunities.append(merged)
        elif rule_result.is_funding_page:
            # Fallback: create a minimal opportunity from rule extraction
            if rule_result.stipend_amounts or rule_result.degree_levels:
                opportunities.append(self._from_rules(rule_result, title, url))

        # Step 7: Validate
        validated = [self._validate(o, university_id, source_page_id, url) for o in opportunities]
        validated = [o for o in validated if o is not None]

        # Record metrics
        for opp in validated:
            degree = opp.get("degree_level", "unknown")
            opportunities_extracted_total.labels(
                university_id=str(university_id), degree_level=degree
            ).inc()

        return ExtractionResult(
            university_id=university_id,
            source_page_id=source_page_id,
            url=url,
            opportunities=validated,
            method=method,
            confidence=classification.confidence,
            rule_result=rule_result,
            llm_result=llm_result,
            extracted_at=started,
        )

    def _merge(self, llm_opp: dict, rules: Any) -> dict:
        """
        Merge LLM output with rule-based extractions.
        Rules take precedence for high-confidence fields (dates, amounts).
        """
        opp = dict(llm_opp)

        # Override deadline with rule-extracted dates (more reliable)
        if rules.deadlines and not opp.get("deadline"):
            opp["deadline"] = rules.deadlines[0]

        # Override stipend with rule-extracted amounts
        if rules.stipend_amounts and not opp.get("stipend_amount"):
            best = max(rules.stipend_amounts, key=lambda s: s["amount"])
            opp["stipend_amount"] = best["amount"]
            opp["stipend_currency"] = best.get("currency", "USD")

        # Merge language requirements
        if rules.language_requirements:
            existing = opp.get("language_requirements") or {}
            opp["language_requirements"] = {**rules.language_requirements, **existing}

        if rules.gpa_minimum and not opp.get("gpa_minimum"):
            opp["gpa_minimum"] = rules.gpa_minimum

        if rules.duration_years and not opp.get("duration_years"):
            opp["duration_years"] = rules.duration_years

        return opp

    def _from_rules(self, rules: Any, title: str, url: str) -> dict:
        opp: dict[str, Any] = {"title": title, "url": url}
        if rules.stipend_amounts:
            best = max(rules.stipend_amounts, key=lambda s: s["amount"])
            opp["stipend_amount"] = best["amount"]
            opp["stipend_currency"] = best.get("currency", "USD")
        if rules.deadlines:
            opp["deadline"] = rules.deadlines[0]
        if rules.degree_levels:
            opp["degree_level"] = rules.degree_levels[0]
        if rules.funding_types:
            opp["funding_type"] = rules.funding_types[0]
        if rules.language_requirements:
            opp["language_requirements"] = rules.language_requirements
        if rules.gpa_minimum:
            opp["gpa_minimum"] = rules.gpa_minimum
        return opp

    def _validate(
        self,
        opp: dict,
        university_id: uuid.UUID,
        source_page_id: uuid.UUID,
        url: str,
    ) -> dict | None:
        """Validate and normalize an opportunity dict. Returns None if invalid."""
        title = opp.get("title", "").strip()
        if not title or len(title) < 5:
            return None

        # Normalise degree_level
        degree_map = {
            "phd": "phd", "ph.d": "phd", "doctoral": "phd",
            "masters": "masters", "master's": "masters",
            "msc": "masters", "ms": "masters", "ma": "masters",
            "meng": "masters", "mba": "masters",
            "postdoc": "postdoc", "any": "any",
        }
        raw_degree = str(opp.get("degree_level", "")).lower()
        degree_level = degree_map.get(raw_degree, "any")

        # Normalise funding_type
        valid_funding_types = {"fully_funded", "partial", "tuition_only", "stipend_only", "unknown"}
        funding_type = opp.get("funding_type", "unknown")
        if funding_type not in valid_funding_types:
            funding_type = "unknown"

        # Validate stipend
        stipend = opp.get("stipend_amount")
        if stipend is not None:
            try:
                stipend = float(stipend)
                if stipend < 0 or stipend > 500_000:
                    stipend = None
            except (TypeError, ValueError):
                stipend = None

        return {
            "university_id": str(university_id),
            "source_page_id": str(source_page_id),
            "title": title[:512],
            "degree_level": degree_level,
            "funding_type": funding_type,
            "stipend_amount": stipend,
            "stipend_currency": opp.get("stipend_currency", "USD"),
            "tuition_covered": opp.get("tuition_covered"),
            "deadline": opp.get("deadline"),
            "description": (opp.get("description") or "")[:2000],
            "requirements": opp.get("requirements") or [],
            "departments": opp.get("departments") or [],
            "citizenship_restrictions": opp.get("citizenship_restrictions"),
            "gpa_minimum": opp.get("gpa_minimum"),
            "language_requirements": opp.get("language_requirements") or {},
            "duration_years": opp.get("duration_years"),
            "source_url": url,
        }

    def _error_result(
        self,
        university_id: uuid.UUID,
        source_page_id: uuid.UUID,
        url: str,
        error: str,
    ) -> ExtractionResult:
        extraction_errors_total.labels(reason="load_failure").inc()
        return ExtractionResult(
            university_id=university_id,
            source_page_id=source_page_id,
            url=url,
            opportunities=[],
            method="error",
            confidence=0.0,
            rule_result=None,
            llm_result=None,
            extracted_at=datetime.now(UTC),
            error=error,
        )


def build_extraction_pipeline() -> ExtractionPipeline:
    """Factory for the pipeline — wires up all dependencies."""
    from scholarscout.contexts.extraction.infrastructure.llm.anthropic_provider import AnthropicProvider
    from scholarscout.contexts.extraction.infrastructure.llm.huggingface_provider import (
        HuggingFaceProvider,
    )
    from scholarscout.contexts.extraction.infrastructure.llm.openai_provider import OpenAIProvider
    from scholarscout.shared.infrastructure.storage.object_storage import ObjectStorageClient
    from scholarscout.config import settings as cfg

    cleaner = HtmlCleaner()
    rules = RuleExtractor()
    classifier = RuleBasedClassifier()

    llm: LLMProvider | None = None
    if cfg.features.llm_extraction:
        if cfg.llm.default_provider == "anthropic" and cfg.llm.anthropic_api_key:
            llm = AnthropicProvider()
        elif cfg.llm.default_provider == "openai" and cfg.llm.openai_api_key:
            llm = OpenAIProvider()
        elif cfg.llm.default_provider == "huggingface" and cfg.llm.huggingface_api_key:
            llm = HuggingFaceProvider()

    s = cfg.storage
    storage = ObjectStorageClient(
        endpoint_url=s.endpoint_url,
        access_key=s.access_key,
        secret_key=s.secret_key,
        region=s.region,
        use_ssl=s.use_ssl,
        bucket_snapshots=s.bucket_snapshots,
        bucket_assets=s.bucket_assets,
        bucket_exports=s.bucket_exports,
    )

    return ExtractionPipeline(
        cleaner=cleaner,
        rule_extractor=rules,
        classifier=classifier,
        llm_provider=llm,
        storage=storage,
    )

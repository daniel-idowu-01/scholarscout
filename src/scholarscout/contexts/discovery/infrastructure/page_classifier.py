"""
Page Classifier — Determines if a crawled page is scholarship-relevant.

Two-stage classification:
1. Fast rule-based heuristics (no I/O, runs inline)
2. Optional ML classification (future: fine-tuned classifier)

Classification output:
  PageType × confidence score [0.0, 1.0]

Training data strategy:
  - Positive: pages we've successfully extracted opportunities from
  - Negative: generic university pages (about, news, events)
  - Store classified pages in PostgreSQL for future model training
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from scholarscout.contexts.crawler.domain.entities import PageType


@dataclass
class ClassificationResult:
    page_type: PageType
    confidence: float
    signals: list[str]


# ── Keyword signals ────────────────────────────────────────────────────────

_TYPE_KEYWORDS: dict[PageType, list[str]] = {
    PageType.SCHOLARSHIP: [
        "scholarship", "scholarships", "award", "bursary", "grant", "merit award",
        "financial award", "prize",
    ],
    PageType.FELLOWSHIP: [
        "fellowship", "fellowships", "postdoctoral fellow", "research fellow",
        "junior fellow", "senior fellow",
    ],
    PageType.ASSISTANTSHIP: [
        "assistantship", "teaching assistant", "research assistant",
        "graduate assistant", "TA position", "RA position", "GTA", "GRA",
    ],
    PageType.GRADUATE: [
        "graduate program", "graduate school", "graduate studies", "graduate funding",
        "phd program", "doctoral program", "master's program", "msc program",
        "postgraduate", "grad school",
    ],
    PageType.ADMISSIONS: [
        "apply now", "application deadline", "how to apply", "admission requirements",
        "application process", "program requirements", "apply for admission",
    ],
    PageType.FUNDING: [
        "fully funded", "stipend", "tuition waiver", "financial support",
        "funding opportunities", "funding available", "funded position",
        "financial aid", "tuition fee", "living allowance",
    ],
    PageType.RESEARCH: [
        "research group", "research lab", "research project", "principal investigator",
        "faculty research", "research opportunities",
    ],
}

# URL path signals
_URL_PATH_PATTERNS: dict[PageType, list[str]] = {
    PageType.SCHOLARSHIP: [r"scholar", r"bursary", r"award"],
    PageType.FELLOWSHIP: [r"fellow", r"postdoc"],
    PageType.ASSISTANTSHIP: [r"assist", r"teaching-?assist", r"research-?assist"],
    PageType.GRADUATE: [r"grad", r"doctoral", r"phd", r"postgrad"],
    PageType.FUNDING: [r"fund", r"stipend", r"financ"],
    PageType.ADMISSIONS: [r"admis", r"apply", r"application"],
}

# Negative signals — pages about these are NOT scholarship pages
_NEGATIVE_SIGNALS = [
    "news article", "press release", "media release", "event registration",
    "campus map", "parking", "dining", "housing", "library hours",
    "athletics", "sports", "alumni giving", "donate",
]


class RuleBasedClassifier:
    """
    Fast, deterministic page classifier.
    Runs in <1ms. No external dependencies.
    """

    def classify(
        self,
        url: str,
        title: str,
        text_sample: str,
        page_type_hint: PageType | None = None,
    ) -> ClassificationResult:
        signals: list[str] = []
        type_scores: dict[PageType, float] = {}

        url_path = urlparse(url).path.lower()
        text_lower = (title + " " + text_sample).lower()

        # URL signals (strong signal)
        for ptype, patterns in _URL_PATH_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_path):
                    type_scores[ptype] = type_scores.get(ptype, 0) + 0.3
                    signals.append(f"url:{pattern}")

        # Text keyword signals
        for ptype, keywords in _TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    type_scores[ptype] = type_scores.get(ptype, 0) + 0.15
                    signals.append(f"kw:{kw}")

        # Negative signals reduce confidence
        for neg in _NEGATIVE_SIGNALS:
            if neg in text_lower:
                for pt in list(type_scores.keys()):
                    type_scores[pt] = type_scores[pt] * 0.5
                signals.append(f"neg:{neg}")

        if not type_scores:
            return ClassificationResult(
                page_type=PageType.UNKNOWN, confidence=0.0, signals=[]
            )

        # Pick the highest-scoring type
        best_type = max(type_scores, key=lambda t: type_scores[t])
        raw_score = type_scores[best_type]

        # Merge GRADUATE and FUNDING into the dominant type
        if best_type in (PageType.GRADUATE, PageType.FUNDING) and raw_score < 0.4:
            # Weak signal — fall back to UNKNOWN
            return ClassificationResult(
                page_type=PageType.UNKNOWN,
                confidence=raw_score,
                signals=signals,
            )

        confidence = min(1.0, raw_score)
        return ClassificationResult(
            page_type=best_type, confidence=confidence, signals=signals
        )

    def is_relevant(self, result: ClassificationResult, threshold: float = 0.25) -> bool:
        """Returns True if the page is worth extracting opportunities from."""
        return (
            result.page_type != PageType.UNKNOWN
            and result.confidence >= threshold
        )

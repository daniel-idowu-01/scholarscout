"""
HTML Cleaner — Produces clean Markdown from raw HTML.

Pipeline:
  raw HTML
    → remove boilerplate (nav, header, footer, ads)
    → extract main content region
    → convert to Markdown (via Trafilatura)
    → post-process: normalize whitespace, fix encoding artifacts

Why Trafilatura:
  Outperforms readability-lxml, boilerpy3, and newspaper3k on
  academic/university web pages in our benchmarks. Preserves
  table structure (important for deadline/funding tables).
"""

from __future__ import annotations

import re
import unicodedata

import trafilatura
from bs4 import BeautifulSoup


_BOILERPLATE_IDS_CLASSES = [
    "header", "footer", "nav", "navigation", "sidebar", "menu",
    "breadcrumb", "cookie-notice", "cookie-banner", "social-share",
    "advertisement", "ads", "ad-container", "related-articles",
    "comments", "comment-section", "share-buttons", "print-only",
    "search-box", "login-form", "newsletter-signup",
]

_REMOVE_TAGS = {"script", "style", "noscript", "iframe", "svg", "form"}


class HtmlCleaner:
    """
    Converts raw HTML into clean Markdown suitable for text extraction.
    """

    def to_markdown(self, html: str) -> str:
        """Main entry point. Returns Markdown string."""
        if not html:
            return ""

        # Try Trafilatura first (best quality)
        md = trafilatura.extract(
            html,
            output_format="markdown",
            include_tables=True,
            include_links=False,  # Remove link spam
            include_images=False,
            favor_recall=True,    # Prefer recall over precision for our use case
            no_fallback=False,
        )

        if md and len(md.strip()) > 100:
            return self._post_process(md)

        # Fallback: manual cleaning
        return self._fallback_extract(html)

    def to_text(self, html: str) -> str:
        """Returns plain text (for classification/short context)."""
        if not html:
            return ""
        text = trafilatura.extract(html, output_format="txt", favor_recall=True) or ""
        if len(text.strip()) > 50:
            return self._post_process(text)
        return self._fallback_extract(html)

    def extract_title(self, html: str) -> str:
        """Extract page title from <title> or <h1>."""
        soup = BeautifulSoup(html, "lxml")
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)[:512]
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)[:512]
        return ""

    def _fallback_extract(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")

        # Remove noise tags
        for tag in soup.find_all(_REMOVE_TAGS):
            tag.decompose()

        # Remove boilerplate elements
        for id_or_class in _BOILERPLATE_IDS_CLASSES:
            for elem in soup.find_all(id=re.compile(id_or_class, re.I)):
                elem.decompose()
            for elem in soup.find_all(class_=re.compile(id_or_class, re.I)):
                elem.decompose()

        text = soup.get_text(separator="\n", strip=True)
        return self._post_process(text)

    @staticmethod
    def _post_process(text: str) -> str:
        # Normalize Unicode
        text = unicodedata.normalize("NFKC", text)

        # Collapse excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove zero-width characters
        text = re.sub(r"[​‌‍﻿­]", "", text)

        # Fix common encoding artifacts
        text = text.replace("’", "'").replace("‘", "'")
        text = text.replace("“", '"').replace("”", '"')
        text = text.replace("—", " - ").replace("–", " - ")

        return text.strip()

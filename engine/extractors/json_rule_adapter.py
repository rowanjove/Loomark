import hashlib
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from engine.extractors.base import BaseExtractor, ExtractedContent

logger = logging.getLogger(__name__)

class JsonRuleExtractor(BaseExtractor):
    """
    CSS Selector JSON Rule Extractor (PRD Section 28).
    Allows extracting structured fields without writing code:
    e.g. {"title": "h1", "content": ".article-body", "author": ".author", "date": "time"}
    """
    def __init__(self, rules: Dict[str, str]):
        self.rules = rules

    def extract(self, html: str, url: str) -> ExtractedContent:
        if not html:
            return ExtractedContent(type=self.rules.get("type", "article"))

        soup = BeautifulSoup(html, "html.parser")

        # Discover links
        discovered_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                discovered_links.append(urljoin(url, href))

        def safe_select_one(selector: Optional[str]):
            if not selector or not isinstance(selector, str):
                return None
            try:
                return soup.select_one(selector)
            except Exception as e:
                logger.warning(f"Invalid CSS selector '{selector}': {e}")
                return None

        # Extract fields based on rules safely
        title = ""
        if "title" in self.rules:
            el = safe_select_one(self.rules["title"])
            if el:
                title = el.get_text().strip()

        content_text = ""
        if "content" in self.rules:
            el = safe_select_one(self.rules["content"])
            if el:
                content_text = el.get_text(separator="\n", strip=True)

        author = ""
        if "author" in self.rules:
            el = safe_select_one(self.rules["author"])
            if el:
                author = el.get_text().strip()

        published_at = None
        if "date" in self.rules:
            el = safe_select_one(self.rules["date"])
            if el:
                published_at = el.get("datetime") or el.get_text().strip()

        clean_text_normalized = " ".join(content_text.split())
        content_hash = hashlib.sha256(clean_text_normalized.encode("utf-8")).hexdigest()

        return ExtractedContent(
            title=title or "Untitled",
            author=author,
            published_at=published_at,
            text=content_text,
            markdown=content_text,
            type=self.rules.get("type", "article"),
            language="zh",
            metadata={"rule_extractor": True},
            links=discovered_links,
            content_hash=content_hash
        )

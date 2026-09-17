import hashlib
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from engine.extractors.base import BaseExtractor, ExtractedContent

class GenericWebsiteExtractor(BaseExtractor):
    """
    General website fallback adapter (PRD Section 22).
    Discovers URLs, extracts metadata, sitemap/RSS hints, and basic text.
    """
    def extract(self, html: str, url: str) -> ExtractedContent:
        if not html:
            return ExtractedContent(type="website")

        soup = BeautifulSoup(html, "html.parser")

        # 1. Discover all links
        discovered_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                full_link = urljoin(url, href)
                discovered_links.append(full_link)

        # 2. Extract title & meta description
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text().strip()

        meta_desc = ""
        desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        if desc_tag and desc_tag.get("content"):
            meta_desc = desc_tag["content"].strip()

        # 3. Detect RSS / Sitemap links in HTML
        feeds = []
        for link in soup.find_all("link", rel=True):
            rel = link.get("rel", [])
            rel_str = " ".join(rel) if isinstance(rel, list) else str(rel)
            if "alternate" in rel_str and link.get("type") in ("application/rss+xml", "application/atom+xml"):
                feed_href = link.get("href")
                if feed_href:
                    feeds.append(urljoin(url, feed_href))

        # 4. Clean text
        for tag in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
            tag.decompose()

        body = soup.find("body") or soup
        text = body.get_text(separator="\n", strip=True) if body else ""

        # Content Hash
        clean_text_normalized = " ".join(text.split())
        content_hash = hashlib.sha256(clean_text_normalized.encode("utf-8")).hexdigest()

        metadata = {
            "description": meta_desc,
            "feeds": feeds
        }

        return ExtractedContent(
            title=title or "Untitled Page",
            author="",
            published_at=None,
            text=text,
            markdown=text,
            type="website",
            language="zh",
            metadata=metadata,
            links=discovered_links,
            content_hash=content_hash
        )

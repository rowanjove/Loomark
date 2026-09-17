import hashlib
import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import trafilatura
from engine.extractors.base import BaseExtractor, ExtractedContent

class GenericArticleExtractor(BaseExtractor):
    """
    Standard article and blog post extractor (PRD Section 21)
    leveraging Trafilatura for heuristic body & metadata parsing,
    with BeautifulSoup fallback for link discovery and structured fields.
    """
    def extract(self, html: str, url: str) -> ExtractedContent:
        if not html:
            return ExtractedContent(type="article")

        # 1. Discover all links using BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        discovered_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                full_link = urljoin(url, href)
                discovered_links.append(full_link)

        # 2. Extract metadata and body via Trafilatura
        extracted_md = trafilatura.extract(
            html,
            url=url,
            output_format="markdown",
            include_links=True,
            include_images=True,
            include_tables=True,
            favor_precision=True
        ) or ""

        # Derive plain text cleanly from markdown without parsing the entire HTML twice
        if extracted_md:
            import re
            clean_t = re.sub(r'!\[.*?\]\(.*?\)', '', extracted_md)
            clean_t = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_t)
            clean_t = re.sub(r'^[#*>\-\s]+', '', clean_t, flags=re.MULTILINE)
            extracted_text = "\n".join(line.strip() for line in clean_t.splitlines() if line.strip())
        else:
            extracted_text = ""

        # Metadata extraction
        metadata = {}
        try:
            meta_obj = trafilatura.extract_metadata(html, default_url=url)
            if meta_obj:
                raw_dict = meta_obj.as_dict()
                for k, v in raw_dict.items():
                    if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                        metadata[k] = v
                    else:
                        metadata[k] = str(v)
        except Exception:
            pass

        title = metadata.get("title") or ""
        author = metadata.get("author") or ""
        date = metadata.get("date") or None

        # Fallback to HTML tags if Trafilatura missed title
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
            elif soup.title and soup.title.string:
                title = soup.title.string.strip()
            elif soup.find("h1"):
                title = soup.find("h1").get_text().strip()

        # Fallback to BeautifulSoup if Trafilatura extracted no text
        if not extracted_text:
            # Remove scripts, styles, nav, header, footer
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
                tag.decompose()
            # Look for main or article tags
            main_tag = soup.find("article") or soup.find("main") or soup.find("body")
            if main_tag:
                extracted_text = main_tag.get_text(separator="\n", strip=True)
                extracted_md = extracted_text

        # Compute SHA-256 content hash for incremental crawl diff
        clean_text_normalized = " ".join(extracted_text.split())
        content_hash = hashlib.sha256(clean_text_normalized.encode("utf-8")).hexdigest()

        return ExtractedContent(
            title=title or "Untitled",
            author=author or "",
            published_at=date,
            text=extracted_text,
            markdown=extracted_md,
            type="article",
            language=metadata.get("language") or "zh",
            metadata=metadata,
            links=discovered_links,
            content_hash=content_hash
        )

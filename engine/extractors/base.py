from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class ExtractedContent:
    title: str = ""
    author: str = ""
    published_at: Optional[str] = None
    text: str = ""
    markdown: str = ""
    type: str = "article" # article, list, video, documentation, forum, unknown
    language: str = "zh"
    metadata: Dict[str, Any] = field(default_factory=dict)
    links: List[str] = field(default_factory=list)
    content_hash: str = ""

class BaseExtractor:
    def extract(self, html: str, url: str) -> ExtractedContent:
        raise NotImplementedError

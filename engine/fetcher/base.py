from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class FetchResult:
    url: str
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    text: str = ""
    raw_bytes: bytes = b""
    response_time_ms: int = 0
    content_type: str = "text/html"
    is_browser_rendered: bool = False
    cookies: Dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None

class BaseFetcher:
    async def fetch(self, url: str, **kwargs) -> FetchResult:
        raise NotImplementedError

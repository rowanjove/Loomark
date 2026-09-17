import hashlib
from typing import Optional, Dict, Any
from engine.db.repository import Repository

from engine.db.session import get_db

def generate_cache_key(content_hash: str, prompt_version: str, model: str) -> str:
    """Generate deterministic cache key for an AI request (PRD Section 46)."""
    raw = f"{content_hash}_{prompt_version}_{model}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

class AICache:
    def __init__(self, repo: Optional[Repository] = None):
        self._repo = repo

    def _is_repo_active(self) -> bool:
        if self._repo is None or self._repo.conn is None:
            return False
        try:
            # Check if underlying sqlite3 connection is still open
            self._repo.conn.total_changes
            return True
        except Exception:
            return False

    def get(self, content_hash: str, prompt_version: str, model: str) -> Optional[Dict[str, Any]]:
        key = generate_cache_key(content_hash, prompt_version, model)
        if self._is_repo_active():
            try:
                return self._repo.get_ai_cache(key)
            except Exception:
                pass
        with get_db() as conn:
            return Repository(conn).get_ai_cache(key)

    def set(self, content_hash: str, prompt_version: str, model: str,
            result: Dict[str, Any], input_tokens: int = 0, output_tokens: int = 0):
        key = generate_cache_key(content_hash, prompt_version, model)
        if self._is_repo_active():
            try:
                self._repo.set_ai_cache(key, result, input_tokens, output_tokens)
                return
            except Exception:
                pass
        with get_db() as conn:
            Repository(conn).set_ai_cache(key, result, input_tokens, output_tokens)

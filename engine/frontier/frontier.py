import asyncio
from typing import List, Dict, Any, Optional
from engine.db.repository import Repository
from engine.frontier.normalizer import normalize_url, is_valid_http_url, is_in_scope

class URLFrontier:
    """
    URL Frontier managing the crawl priority queue, deduplication,
    crash recovery, and URL lifecycle states.
    """
    def __init__(self, repo: Repository, job_id: str, project_id: str,
                 scope: str = "domain", scope_regex: Optional[str] = None,
                 max_depth: int = 3, max_pages: int = 100,
                 seen_hashes: Optional[set] = None):
        self.repo = repo
        self.job_id = job_id
        self.project_id = project_id
        self.scope = scope
        self.scope_regex = scope_regex
        self.max_depth = max_depth
        self.max_pages = max_pages
        self._seen_hashes: set = seen_hashes if seen_hashes is not None else set()

    def add_seeds(self, seed_urls: List[str]) -> int:
        """Add initial entrypoint URLs with priority 100, depth 0."""
        entries = []
        for url in seed_urls:
            if not is_valid_http_url(url):
                continue
            norm_url, url_hash, domain = normalize_url(url)
            if self.repo.check_url_exists_in_job(self.job_id, url_hash):
                continue
            self._seen_hashes.add(url_hash)
            entries.append({
                "job_id": self.job_id,
                "project_id": self.project_id,
                "url": url,
                "normalized_url": norm_url,
                "url_hash": url_hash,
                "domain": domain,
                "depth": 0,
                "priority": 100,
                "status": "QUEUED",
                "parent_url": None
            })
        return self.repo.insert_urls_batch(entries)

    def add_discovered_links(self, links: List[str], parent_url: str,
                             parent_depth: int, seed_url: str) -> int:
        """Filter discovered links by scope and depth, then batch insert."""
        target_depth = parent_depth + 1
        if self.max_depth > 0 and target_depth > self.max_depth:
            return 0

        entries = []
        for link in links:
            if not is_valid_http_url(link):
                continue
            norm_url, url_hash, domain = normalize_url(link)

            # In-memory fast dedup check
            if url_hash in self._seen_hashes:
                continue

            # Check scope restriction
            if not is_in_scope(norm_url, seed_url, self.scope, self.scope_regex):
                continue

            self._seen_hashes.add(url_hash)
            # Priority drops as depth increases
            priority = max(1, 50 - target_depth * 10)
            entries.append({
                "job_id": self.job_id,
                "project_id": self.project_id,
                "url": link,
                "normalized_url": norm_url,
                "url_hash": url_hash,
                "domain": domain,
                "depth": target_depth,
                "priority": priority,
                "status": "QUEUED",
                "parent_url": parent_url
            })

        return self.repo.insert_urls_batch(entries)

    def pop_next(self, eligible_domains: Optional[List[str]] = None, limit: int = 1) -> List[Dict[str, Any]]:
        """Retrieve the next queued URLs and transition them to FETCHING."""
        urls = self.repo.pop_next_urls_for_domains(self.job_id, eligible_domains or [], limit)
        for u in urls:
            self.repo.update_url_status(u["id"], "FETCHING")
        return urls

    def mark_completed(self, url_id: str):
        self.repo.update_url_status(url_id, "PARSED")

    def mark_failed(self, url_id: str, error_message: str, can_retry: bool = False, max_retries: int = 3):
        if can_retry:
            self.repo.increment_url_retry(url_id, error_message)
        else:
            self.repo.update_url_status(url_id, "FAILED", error_message)

    def mark_skipped(self, url_id: str, reason: str = "Max pages reached or out of scope"):
        self.repo.update_url_status(url_id, "SKIPPED", reason)

    def get_stats(self) -> Dict[str, int]:
        return self.repo.get_job_url_counts(self.job_id)

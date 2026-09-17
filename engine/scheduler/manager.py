import asyncio
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from engine.db.session import get_db
from engine.db.repository import Repository
from engine.frontier.frontier import URLFrontier
from engine.frontier.rate_limiter import DomainRateLimiter
from engine.fetcher.http_fetcher import HttpFetcher
from engine.fetcher.smart_fetcher import SmartFetcher
from engine.extractors.generic_article import GenericArticleExtractor
from engine.extractors.generic_website import GenericWebsiteExtractor
from engine.extractors.json_rule_adapter import JsonRuleExtractor
from engine.extractors.media_subtitle import MediaSubtitleExtractor
from engine.extractors.plugin_manager import plugin_manager
from engine.ai.worker import AIQueueWorker
from engine.scheduler.event_bus import event_bus
from engine.config import PROJECTS_DATA_DIR, CONCURRENCY_PRESETS

logger = logging.getLogger(__name__)

class CrawlJobRunner:
    """
    Executes a single crawl job asynchronously, managing concurrency,
    rate limiting, extraction, raw HTML persistence, and diff detection.
    """
    def __init__(self, job_id: str, project_id: str, config: Dict[str, Any],
                 ai_worker: Optional[AIQueueWorker] = None):
        self.job_id = job_id
        self.project_id = project_id
        self.config = config
        self.ai_worker = ai_worker
        self.is_paused = False
        self.is_stopped = False
        self._task: Optional[asyncio.Task] = None

        # Resolve concurrency preset
        preset_name = config.get("preset", "balanced")
        preset = CONCURRENCY_PRESETS.get(preset_name, CONCURRENCY_PRESETS["balanced"])
        self.max_concurrent = config.get("max_concurrent") or preset["max_concurrent"]
        self.domain_concurrent = config.get("domain_concurrent") or preset["domain_concurrent"]
        self.domain_delay_ms = config.get("domain_delay_ms") or preset["domain_delay_ms"]
        self.max_pages = config.get("max_pages", 100)
        self.max_depth = config.get("max_depth", 3)
        self.scope = config.get("scope", "domain")
        self.scope_regex = config.get("scope_regex")
        self.fetch_mode = config.get("fetch_mode", "smart")

        self.rate_limiter = DomainRateLimiter(self.domain_concurrent, self.domain_delay_ms)
        self.http_fetcher = HttpFetcher(timeout_seconds=preset["timeout_seconds"])
        if self.fetch_mode == "browser":
            try:
                from engine.fetcher.browser_fetcher import BrowserFetcher
                self.fetcher = BrowserFetcher(timeout_seconds=preset["timeout_seconds"])
            except Exception:
                self.fetcher = SmartFetcher(self.http_fetcher)
        elif self.fetch_mode == "smart":
            self.fetcher = SmartFetcher(self.http_fetcher)
        else:
            self.fetcher = self.http_fetcher

        # Select extractor
        adapter_id = config.get("adapter_id", "auto")
        if adapter_id == "website":
            self.extractor = GenericWebsiteExtractor()
        elif adapter_id.startswith("rule:"):
            # Custom JSON rule adapter
            try:
                rule_dict = json.loads(adapter_id[5:])
                self.extractor = JsonRuleExtractor(rule_dict)
            except Exception as e:
                logger.warning(f"Failed to parse inline rule adapter: {e}")
                self.extractor = GenericArticleExtractor()
        elif adapter_id.startswith("plugin:"):
            plugin_id = adapter_id[7:]
            p = plugin_manager.get_plugin(plugin_id)
            if p and p.get("rules"):
                self.extractor = JsonRuleExtractor(p["rules"])
            else:
                self.extractor = GenericArticleExtractor()
        elif adapter_id not in ("auto", "article", "video"):
            # Check if adapter_id is a known plugin ID
            p = plugin_manager.get_plugin(adapter_id)
            if p and p.get("rules"):
                self.extractor = JsonRuleExtractor(p["rules"])
            else:
                self.extractor = GenericArticleExtractor()
        else:
            self.extractor = GenericArticleExtractor()

        self.media_extractor = MediaSubtitleExtractor()

        # Stats tracking
        self.start_time = time.monotonic()
        self.pages_processed = 0
        self.seed_url = ""
        self.seen_hashes: set = set()

    async def log(self, level: str, message: str, repo: Repository):
        ts = datetime.now().strftime("%H:%M:%S")
        repo.add_crawl_log(self.job_id, level, f"{ts} {message}")
        await event_bus.broadcast_log(self.job_id, level, message, ts)

    async def run(self, seed_urls: List[str]):
        if seed_urls:
            self.seed_url = seed_urls[0]

        snapshots_dir = PROJECTS_DATA_DIR / self.project_id / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        with get_db() as conn:
            repo = Repository(conn)
            repo.update_job_status(self.job_id, "RUNNING", started=True)
            frontier = URLFrontier(
                repo=repo,
                job_id=self.job_id,
                project_id=self.project_id,
                scope=self.scope,
                scope_regex=self.scope_regex,
                max_depth=self.max_depth,
                max_pages=self.max_pages,
                seen_hashes=self.seen_hashes
            )
            # Add initial seeds
            if seed_urls:
                added = frontier.add_seeds(seed_urls)
                await self.log("INFO", f"Seeds added: {added} URL(s)", repo)

        semaphore = asyncio.Semaphore(self.max_concurrent)
        active_tasks: set[asyncio.Task] = set()

        try:
            while not self.is_stopped:
                if self.is_paused:
                    await asyncio.sleep(0.5)
                    continue

                if self.max_pages > 0 and self.pages_processed >= self.max_pages:
                    with get_db() as conn:
                        repo = Repository(conn)
                        await self.log("INFO", f"Reached max pages limit ({self.max_pages}). Finishing job.", repo)
                    break

                # Pop new URLs to fill available concurrency slots
                available_slots = self.max_concurrent - len(active_tasks)
                if available_slots > 0:
                    with get_db() as conn:
                        repo = Repository(conn)
                        frontier = URLFrontier(
                            repo, self.job_id, self.project_id, self.scope,
                            self.scope_regex, self.max_depth, self.max_pages,
                            seen_hashes=self.seen_hashes
                        )
                        next_batch = frontier.pop_next(limit=available_slots)

                    for u in next_batch:
                        task = asyncio.create_task(self._process_single_url(u, semaphore, snapshots_dir))
                        active_tasks.add(task)

                if not active_tasks:
                    # Check if there are in-flight URLs in DB or queue is truly exhausted
                    with get_db() as conn:
                        repo = Repository(conn)
                        stats = repo.get_job_url_counts(self.job_id)
                        if stats["FETCHING"] == 0 and stats["QUEUED"] == 0:
                            await self.log("INFO", "Queue exhausted. All URLs processed.", repo)
                            break
                    await asyncio.sleep(0.3)
                    continue

                # Wait for any active task to finish to immediately free up concurrency slots
                done, active_tasks = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)

                # Broadcast current stats
                elapsed = max(0.1, time.monotonic() - self.start_time)
                rate = round(self.pages_processed / elapsed, 2)
                with get_db() as conn:
                    repo = Repository(conn)
                    counts = repo.get_job_url_counts(self.job_id)
                    counts["pages_per_second"] = rate
                    repo.update_job_stats(self.job_id, counts)
                    await event_bus.broadcast_job_stats(self.job_id, counts)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in crawl job loop: {e}", exc_info=True)
            with get_db() as conn:
                repo = Repository(conn)
                await self.log("ERROR", f"Job loop encountered critical error: {e}", repo)
                repo.update_job_status(self.job_id, "FAILED")
            return
        finally:
            # Drain or cancel any remaining in-flight tasks
            if active_tasks:
                for t in active_tasks:
                    if not t.done():
                        t.cancel()
                await asyncio.gather(*active_tasks, return_exceptions=True)

            await self.fetcher.close()
            with get_db() as conn:
                repo = Repository(conn)
                final_status = "PAUSED" if self.is_paused else ("STOPPED" if self.is_stopped else "COMPLETED")
                repo.update_job_status(self.job_id, final_status, finished=(final_status == "COMPLETED"))
                counts = repo.get_job_url_counts(self.job_id)
                repo.update_job_stats(self.job_id, counts)
                await event_bus.broadcast_job_stats(self.job_id, counts)
                await self.log("INFO", f"Job ended with status: {final_status}", repo)

    async def _process_single_url(self, url_item: Dict[str, Any],
                                  semaphore: asyncio.Semaphore,
                                  snapshots_dir: Path):
        url_id = url_item["id"]
        target_url = url_item["url"]
        domain = url_item["domain"]
        depth = url_item["depth"]
        url_hash = url_item["url_hash"]

        async with semaphore:
            await self.rate_limiter.acquire(domain)
            try:
                ts = datetime.now().strftime("%H:%M:%S")
                await event_bus.broadcast_log(self.job_id, "INFO", f"FETCH {target_url}", ts)

                fetch_res = await self.fetcher.fetch(target_url)

                if fetch_res.status_code == 0 or fetch_res.error:
                    with get_db() as conn:
                        repo = Repository(conn)
                        frontier = URLFrontier(repo, self.job_id, self.project_id, seen_hashes=self.seen_hashes)
                        frontier.mark_failed(url_id, fetch_res.error or "Network error", can_retry=(url_item["retry_count"] < 3))
                        await self.log("WARNING", f"FAIL {target_url}: {fetch_res.error}", repo)
                    return

                # Save raw HTML to project snapshot storage via thread (PRD Section 37)
                raw_file_name = f"{url_hash[:16]}_{int(time.time())}.html"
                raw_path = snapshots_dir / raw_file_name

                def write_snapshot_file():
                    with open(raw_path, "w", encoding="utf-8", errors="replace") as f:
                        f.write(fetch_res.text)

                await asyncio.to_thread(write_snapshot_file)

                # Extract content using two-tier adapter resolution (PRD Section 21-28)
                from engine.extractors.plugin_manager import plugin_manager
                active_extractor = self.extractor
                if self.config.get("adapter_id", "auto") == "auto":
                    site_extractor = plugin_manager.find_matching_extractor(target_url)
                    if site_extractor:
                        active_extractor = site_extractor

                extracted = await asyncio.to_thread(active_extractor.extract, fetch_res.text, target_url)

                # Check and extract video/subtitles if target is a video platform URL
                media_info = None
                is_media_url = (
                    any(d in domain for d in ("youtube.com", "youtu.be", "bilibili.com"))
                    or self.config.get("adapter_id") == "video"
                )
                if is_media_url:
                    try:
                        media_info = await self.media_extractor.extract_media_info(target_url)
                        if media_info and media_info.get("title"):
                            extracted.title = media_info["title"]
                            extracted.author = media_info.get("uploader") or extracted.author
                            extracted.type = "video"
                            if media_info.get("description"):
                                extracted.text = media_info["description"]
                                extracted.markdown = f"# {extracted.title}\n\n{media_info['description']}"
                    except Exception as me:
                        logger.debug(f"Media extraction skipped for {target_url}: {me}")

                with get_db() as conn:
                    repo = Repository(conn)
                    frontier = URLFrontier(
                        repo, self.job_id, self.project_id, self.scope,
                        self.scope_regex, self.max_depth, self.max_pages,
                        seen_hashes=self.seen_hashes
                    )

                    # Incremental Change Detection (PRD Section 38-39)
                    prev_doc = repo.get_latest_document_by_url_hash(self.project_id, url_hash)
                    old_hash = prev_doc["content_hash"] if prev_doc else repo.get_latest_content_hash(self.project_id, url_hash)
                    if old_hash is None:
                        change_status = "NEW"
                        diff_summary = None
                    elif old_hash == extracted.content_hash:
                        change_status = "UNCHANGED"
                        diff_summary = "Content unchanged from previous capture."
                    else:
                        change_status = "UPDATED"
                        diff_summary = "Content hash changed. Content updated."

                    # Store Snapshot
                    snap_id = repo.create_snapshot(
                        url_id=url_id,
                        job_id=self.job_id,
                        project_id=self.project_id,
                        status_code=fetch_res.status_code,
                        headers=fetch_res.headers,
                        raw_html_path=str(raw_path),
                        content_hash=extracted.content_hash,
                        response_time_ms=fetch_res.response_time_ms
                    )

                    # Store Document only if content changed or if not previously indexed (avoid FTS redundancy)
                    if change_status != "UNCHANGED" or not prev_doc:
                        doc_id = repo.create_document(
                            snapshot_id=snap_id,
                            project_id=self.project_id,
                            url_id=url_id,
                            doc_type=extracted.type,
                            title=extracted.title,
                            author=extracted.author,
                            published_at=extracted.published_at,
                            text=extracted.text,
                            markdown=extracted.markdown,
                            language=extracted.language,
                            metadata=extracted.metadata,
                            content_hash=extracted.content_hash,
                            change_status=change_status,
                            diff_summary=diff_summary
                        )
                    else:
                        doc_id = prev_doc["id"]

                    # Store Subtitles if extracted
                    if media_info:
                        parsed_subs = media_info.get("subtitles_parsed") or {}
                        for lang, segs in parsed_subs.items():
                            if segs:
                                repo.create_subtitle(
                                    document_id=doc_id,
                                    language=lang,
                                    source="auto",
                                    segments=segs
                                )

                    # Mark URL as completed
                    frontier.mark_completed(url_id)
                    self.pages_processed += 1

                    # Discover & Queue Outbound Links
                    new_links_count = frontier.add_discovered_links(
                        links=extracted.links,
                        parent_url=target_url,
                        parent_depth=depth,
                        seed_url=self.seed_url or target_url
                    )

                    await self.log("INFO", f"PARSED [{fetch_res.status_code}] {extracted.title[:40]} (+{new_links_count} links)", repo)

                    # Enqueue AI summary if enabled and document is new/updated
                    if self.config.get("enable_ai_summary") and self.ai_worker and change_status != "UNCHANGED":
                        self.ai_worker.enqueue_document(
                            document_id=doc_id,
                            project_id=self.project_id,
                            task_type="article_summary_v1",
                            model=self.config.get("ai_model")
                        )

            except Exception as e:
                logger.error(f"Error processing {target_url}: {e}", exc_info=True)
                with get_db() as conn:
                    repo = Repository(conn)
                    frontier = URLFrontier(repo, self.job_id, self.project_id)
                    frontier.mark_failed(url_id, str(e))
                    await self.log("ERROR", f"ERROR {target_url}: {e}", repo)
            finally:
                self.rate_limiter.release(domain)

class CrawlManager:
    """
    Global manager for crawl runners with Start, Pause, Resume, Stop, Retry controls.
    """
    def __init__(self, ai_worker: Optional[AIQueueWorker] = None):
        self.runners: Dict[str, CrawlJobRunner] = {}
        self.ai_worker = ai_worker

    def start_job(self, job_id: str, project_id: str, config: Dict[str, Any],
                  seed_urls: List[str]) -> CrawlJobRunner:
        if job_id in self.runners and not self.runners[job_id].is_stopped:
            return self.runners[job_id]

        runner = CrawlJobRunner(job_id, project_id, config, self.ai_worker)
        self.runners[job_id] = runner
        runner._task = asyncio.create_task(runner.run(seed_urls))
        return runner

    def pause_job(self, job_id: str):
        if job_id in self.runners:
            self.runners[job_id].is_paused = True
        with get_db() as conn:
            Repository(conn).update_job_status(job_id, "PAUSED")

    def resume_job(self, job_id: str) -> Optional[CrawlJobRunner]:
        if job_id in self.runners:
            runner = self.runners[job_id]
            runner.is_paused = False
            runner.is_stopped = False
            with get_db() as conn:
                Repository(conn).update_job_status(job_id, "RUNNING")
            if runner._task is None or runner._task.done():
                runner._task = asyncio.create_task(runner.run([]))
            return runner
        else:
            # Cold-start / post-restart recovery from database
            with get_db() as conn:
                repo = Repository(conn)
                job = repo.get_crawl_job(job_id)
                if job and job["status"] in ("PAUSED", "RUNNING", "STOPPED", "FAILED"):
                    config = json.loads(job["config_json"]) if isinstance(job.get("config_json"), str) else (job.get("config_json") or {})
                    runner = CrawlJobRunner(job_id, job["project_id"], config, self.ai_worker)
                    self.runners[job_id] = runner
                    repo.update_job_status(job_id, "RUNNING")
                    runner._task = asyncio.create_task(runner.run([]))
                    return runner
            return None

    def stop_job(self, job_id: str):
        if job_id in self.runners:
            runner = self.runners[job_id]
            runner.is_stopped = True
            if runner._task and not runner._task.done():
                runner._task.cancel()
        with get_db() as conn:
            Repository(conn).update_job_status(job_id, "STOPPED")

    def retry_job(self, job_id: str) -> int:
        with get_db() as conn:
            repo = Repository(conn)
            count = repo.retry_all_failed_urls(job_id)
        self.resume_job(job_id)
        return count

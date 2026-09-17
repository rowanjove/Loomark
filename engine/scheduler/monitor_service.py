import asyncio
import logging
from typing import Optional
from datetime import datetime
from engine.db.session import get_db
from engine.db.repository import Repository
from engine.frontier.normalizer import normalize_url
from engine.fetcher.smart_fetcher import SmartFetcher
from engine.extractors.plugin_manager import plugin_manager
from engine.extractors.generic_article import GenericArticleExtractor
from engine.ai.client import AIProviderClient
from engine.scheduler.event_bus import event_bus

logger = logging.getLogger(__name__)

class MonitorService:
    """
    Website Monitoring Engine (PRD Section 75-77, 104).
    Performs periodic automated incremental checks of scheduled URLs,
    records change events (NEW, UPDATED, UNCHANGED, ERROR),
    and triggers AI Change Summaries on content modifications.
    """
    def __init__(self, ai_client: Optional[AIProviderClient] = None, check_interval_sec: int = 30):
        self.ai_client = ai_client
        self.check_interval_sec = check_interval_sec
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.fetcher = SmartFetcher()

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._monitor_loop())
            logger.info("MonitorService background engine started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("MonitorService stopped.")

    async def _monitor_loop(self):
        while self._running:
            try:
                await self._check_due_schedules()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in MonitorService loop: {e}", exc_info=True)

            await asyncio.sleep(self.check_interval_sec)

    async def _check_due_schedules(self):
        with get_db() as conn:
            repo = Repository(conn)
            due_schedules = repo.get_due_monitor_schedules()

        for sched in due_schedules:
            if not self._running:
                break
            try:
                await self._run_single_check(sched)
            except Exception as e:
                logger.error(f"Error checking schedule {sched['id']} ({sched['url']}): {e}")

    async def _run_single_check(self, schedule: dict):
        sched_id = schedule["id"]
        project_id = schedule["project_id"]
        url = schedule["url"]
        interval = schedule["interval_minutes"]

        norm_url, url_hash, domain = normalize_url(url)

        sched_type = schedule.get("schedule_type", "interval")
        cron_expr = schedule.get("cron_expression")

        # 1. Fetch content
        fetch_res = await self.fetcher.fetch(url)

        with get_db() as conn:
            repo = Repository(conn)
            if fetch_res.status_code == 0 or fetch_res.error:
                repo.create_monitor_event(
                    project_id=project_id,
                    schedule_id=sched_id,
                    url=url,
                    event_type="ERROR",
                    ai_change_summary=f"连接失败: {fetch_res.error or '无法访问'}"
                )
                repo.update_monitor_schedule_run(sched_id, interval, schedule_type=sched_type, cron_expression=cron_expr)
                return

            # 2. Extract content using site-specific or generic adapter
            site_extractor = plugin_manager.find_matching_extractor(url)
            extractor = site_extractor or GenericArticleExtractor()
            extracted = extractor.extract(fetch_res.text, url)

            # 3. Check for previous content hash
            old_hash = repo.get_latest_content_hash(project_id, url_hash)

            ai_summary = None
            if old_hash is None:
                event_type = "NEW"
                ai_summary = "首次监控收录页面。"
            elif old_hash == extracted.content_hash:
                event_type = "UNCHANGED"
                ai_summary = "页面内容未发生任何改变。"
            else:
                event_type = "UPDATED"
                # If AI is configured, request AI change analysis
                if self.ai_client:
                    try:
                        # Fetch the previous document snippet by url_hash
                        prev_doc = repo.get_latest_document_by_url_hash(project_id, url_hash)
                        old_snippet = (prev_doc["text"] or prev_doc["markdown"] if prev_doc else "")[:4000]
                        new_snippet = (extracted.text or extracted.markdown or "")[:4000]

                        ai_res = await self.ai_client.execute_task(
                            task_type="change_analysis_v1",
                            content=new_snippet,
                            title=extracted.title,
                            content_hash=extracted.content_hash,
                            extra_params={
                                "old_content": old_snippet or "（首次抓取，无前序版本）",
                                "new_content": new_snippet
                            }
                        )
                        if "error" not in ai_res:
                            ai_summary = ai_res["result"].get("text")
                    except Exception as ai_e:
                        logger.warning(f"AI Change analysis error: {ai_e}")
                        ai_summary = "页面正文哈希发生改变（AI 摘要生成失败）。"
                else:
                    ai_summary = "页面正文哈希发生改变，检测到新内容更新。"

            # 4. Record event & persist baseline snapshot on change
            if event_type in ("NEW", "UPDATED"):
                try:
                    # Find or create associated URL record and job_id to satisfy foreign key constraints
                    existing_url = conn.execute(
                        "SELECT id, job_id FROM urls WHERE project_id = ? AND url_hash = ? ORDER BY created_at DESC LIMIT 1;",
                        (project_id, url_hash)
                    ).fetchone()

                    if existing_url:
                        target_url_id = existing_url["id"]
                        target_job_id = existing_url["job_id"]
                    else:
                        # Ensure a monitoring job exists for this project
                        m_job = conn.execute(
                            "SELECT id FROM crawl_jobs WHERE project_id = ? AND name = 'Website Monitoring' LIMIT 1;",
                            (project_id,)
                        ).fetchone()
                        if m_job:
                            target_job_id = m_job["id"]
                        else:
                            new_job = repo.create_crawl_job(
                                project_id=project_id,
                                name="Website Monitoring",
                                config={"type": "monitoring"}
                            )
                            target_job_id = new_job["id"]

                        url_entry = repo.create_url(
                            project_id=project_id,
                            url=url,
                            normalized_url=norm_url,
                            url_hash=url_hash,
                            domain=domain,
                            status="FETCHED",
                            job_id=target_job_id
                        )
                        target_url_id = url_entry["id"]

                    # Persist snapshot so subsequent checks can match against this new hash
                    snap_id = repo.create_snapshot(
                        url_id=target_url_id,
                        job_id=target_job_id,
                        project_id=project_id,
                        status_code=fetch_res.status_code,
                        headers=fetch_res.headers,
                        raw_html_path=None,
                        content_hash=extracted.content_hash,
                        response_time_ms=fetch_res.response_time_ms
                    )

                    repo.create_document(
                        snapshot_id=snap_id,
                        project_id=project_id,
                        url_id=target_url_id,
                        doc_type=extracted.type,
                        title=extracted.title,
                        author=extracted.author,
                        published_at=extracted.published_at,
                        text=extracted.text,
                        markdown=extracted.markdown,
                        language=extracted.language,
                        metadata=extracted.metadata,
                        content_hash=extracted.content_hash,
                        change_status=event_type,
                        diff_summary=ai_summary
                    )
                except Exception as save_err:
                    logger.warning(f"Failed to persist updated snapshot baseline for {url}: {save_err}")

            repo.create_monitor_event(
                project_id=project_id,
                schedule_id=sched_id,
                url=url,
                event_type=event_type,
                old_content_hash=old_hash,
                new_content_hash=extracted.content_hash,
                ai_change_summary=ai_summary
            )

            # Update schedule run time
            repo.update_monitor_schedule_run(sched_id, interval, schedule_type=sched_type, cron_expression=cron_expr)
            logger.info(f"Monitor check completed for {url}: {event_type}")

# Global monitor service instance
monitor_service = MonitorService()

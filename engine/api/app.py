import os
import asyncio
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse

from engine.db.session import init_db, get_db
from engine.db.repository import Repository
from engine.db.models import (
    ProjectCreate, ProjectOut, TargetCreate, TargetOut,
    CrawlJobCreate, CrawlJobOut, DocumentOut, StatsSummary
)
from engine.ai.client import AIProviderClient
from engine.ai.worker import AIQueueWorker
from engine.scheduler.manager import CrawlManager
from engine.scheduler.event_bus import event_bus
from engine.exporter.export_service import ExportService
from engine.fetcher.http_fetcher import HttpFetcher
from engine.extractors.generic_article import GenericArticleExtractor
from engine.extractors.generic_website import GenericWebsiteExtractor
from engine.config import load_settings, save_settings, DEFAULT_USER_AGENT
from engine.frontier.normalizer import normalize_url, is_safe_url

# Global workers
ai_client: Optional[AIProviderClient] = None
ai_worker: Optional[AIQueueWorker] = None
crawl_manager: Optional[CrawlManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ai_client, ai_worker, crawl_manager
    init_db()

    # Try to initialize AI client from persisted settings or environment
    settings = load_settings()
    ai_settings = settings.get("ai", {})
    api_key = ai_settings.get("api_key") or os.getenv("OPENAI_API_KEY")
    base_url = ai_settings.get("base_url") or os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    model = ai_settings.get("model") or os.getenv("OPENAI_MODEL", "deepseek-chat")

    if api_key:
        ai_client = AIProviderClient(api_key=api_key, base_url=base_url, default_model=model)

    ai_worker = AIQueueWorker(ai_client=ai_client)
    ai_worker.start()
    crawl_manager = CrawlManager(ai_worker)

    from engine.scheduler.monitor_service import monitor_service
    monitor_service.ai_client = ai_client
    monitor_service.start()

    yield

    if ai_worker:
        ai_worker.stop()
    monitor_service.stop()
    try:
        from engine.fetcher.browser_pool import global_browser_pool
        await global_browser_pool.close()
    except Exception:
        pass

app = FastAPI(title="Loomark Crawler Engine", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "engine": "Loomark", "version": "1.0.0"}

# --- Projects ---
@app.get("/api/projects", response_model=List[ProjectOut])
def list_projects():
    with get_db() as conn:
        repo = Repository(conn)
        return repo.list_projects()

@app.post("/api/projects", response_model=ProjectOut)
def create_project(data: ProjectCreate):
    with get_db() as conn:
        repo = Repository(conn)
        return repo.create_project(name=data.name, description=data.description or "")

@app.get("/api/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str):
    with get_db() as conn:
        repo = Repository(conn)
        proj = repo.get_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
        return proj

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    with get_db() as conn:
        repo = Repository(conn)
        if not repo.delete_project(project_id):
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True}

# --- Targets ---
@app.get("/api/projects/{project_id}/targets", response_model=List[TargetOut])
def list_targets(project_id: str):
    with get_db() as conn:
        repo = Repository(conn)
        return repo.list_targets(project_id)

@app.post("/api/projects/{project_id}/targets", response_model=TargetOut)
def create_target(project_id: str, data: TargetCreate):
    with get_db() as conn:
        repo = Repository(conn)
        return repo.create_target(
            project_id=project_id,
            url=data.url,
            scope=data.scope,
            scope_regex=data.scope_regex,
            adapter_id=data.adapter_id
        )

# --- Crawl Jobs ---
@app.post("/api/crawls", response_model=CrawlJobOut)
def create_and_start_crawl(data: CrawlJobCreate):
    with get_db() as conn:
        repo = Repository(conn)
        job = repo.create_crawl_job(
            project_id=data.project_id,
            name=data.name,
            config=data.config.model_dump(),
            target_id=data.target_id
        )
    # Start crawl runner
    seed_urls = data.urls
    if not seed_urls and data.target_id:
        with get_db() as conn:
            repo = Repository(conn)
            targets = repo.list_targets(data.project_id)
            target = next((t for t in targets if t["id"] == data.target_id), None)
            if target:
                seed_urls = [target["url"]]

    crawl_manager.start_job(job["id"], data.project_id, data.config.model_dump(), seed_urls)
    return job

@app.get("/api/crawls", response_model=List[CrawlJobOut])
def list_crawl_jobs(project_id: Optional[str] = None):
    with get_db() as conn:
        repo = Repository(conn)
        return repo.list_crawl_jobs(project_id)

@app.get("/api/crawls/{job_id}", response_model=CrawlJobOut)
def get_crawl_job(job_id: str):
    with get_db() as conn:
        repo = Repository(conn)
        job = repo.get_crawl_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

@app.post("/api/crawls/{job_id}/pause")
def pause_crawl(job_id: str):
    crawl_manager.pause_job(job_id)
    return {"status": "paused"}

@app.post("/api/crawls/{job_id}/resume")
def resume_crawl(job_id: str):
    crawl_manager.resume_job(job_id)
    return {"status": "resumed"}

@app.post("/api/crawls/{job_id}/stop")
def stop_crawl(job_id: str):
    crawl_manager.stop_job(job_id)
    return {"status": "stopped"}

@app.post("/api/crawls/{job_id}/retry")
def retry_crawl_failed(job_id: str):
    count = crawl_manager.retry_job(job_id)
    return {"retried_count": count}

@app.get("/api/crawls/{job_id}/logs")
def get_crawl_logs(job_id: str, limit: int = 100):
    with get_db() as conn:
        repo = Repository(conn)
        return repo.get_job_logs(job_id, limit=limit)

# --- Documents & FTS/Semantic Hybrid Search ---
@app.get("/api/projects/{project_id}/documents")
def list_documents(
    project_id: str,
    search: Optional[str] = None,
    search_mode: str = Query("hybrid", regex="^(fts|semantic|hybrid)$"),
    domain: Optional[str] = None,
    doc_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    with get_db() as conn:
        repo = Repository(conn)
        if search and search.strip():
            docs, total = repo.hybrid_search_documents(
                project_id=project_id,
                query=search.strip(),
                mode=search_mode,
                domain=domain,
                doc_type=doc_type,
                limit=limit,
                offset=offset
            )
        else:
            docs, total = repo.list_documents(
                project_id=project_id,
                search=None,
                domain=domain,
                doc_type=doc_type,
                limit=limit,
                offset=offset
            )
        return {"items": docs, "total": total, "limit": limit, "offset": offset, "search_mode": search_mode}

@app.get("/api/documents/{document_id}")
def get_document(document_id: str):
    with get_db() as conn:
        repo = Repository(conn)
        doc = repo.get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return doc

@app.get("/api/documents/{document_id}/chunks")
def get_document_chunks(document_id: str):
    """Get or dynamically generate document semantic chunks (PRD Section 45, 52)."""
    with get_db() as conn:
        repo = Repository(conn)
        doc = repo.get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        from engine.ai.chunker import process_and_save_chunks
        chunks = process_and_save_chunks(
            repo=repo,
            document_id=document_id,
            project_id=doc["project_id"],
            text=doc.get("text") or doc.get("markdown") or ""
        )
        return chunks

@app.get("/api/documents/{document_id}/history")
def get_document_history(document_id: str):
    with get_db() as conn:
        repo = Repository(conn)
        return repo.get_document_snapshots_history(document_id)

@app.get("/api/documents/{document_id}/subtitles")
def get_document_subtitles(document_id: str):
    with get_db() as conn:
        repo = Repository(conn)
        return repo.get_subtitles_for_document(document_id)


@app.get("/api/documents/{document_id}/ai")
def get_document_ai_artifacts(document_id: str):
    with get_db() as conn:
        repo = Repository(conn)
        return repo.get_ai_artifacts_for_document(document_id)

@app.post("/api/documents/{document_id}/ai")
async def trigger_document_ai(
    document_id: str,
    task_type: str = Body("article_summary_v1"),
    model: Optional[str] = Body(None)
):
    global ai_client
    if not ai_client:
        raise HTTPException(status_code=400, detail="AI Provider is not configured. Please set API Key in settings.")

    with get_db() as conn:
        repo = Repository(conn)
        doc = repo.get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

    from engine.ai.cache import AICache
    cache = AICache()
    res = await ai_client.execute_task(
        task_type=task_type,
        content=doc["text"] or doc["markdown"],
        title=doc["title"],
        model=model,
        cache=cache,
        content_hash=doc["content_hash"]
    )

    if "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])

    with get_db() as conn:
        repo = Repository(conn)
        art_id = repo.create_ai_artifact(
            document_id=document_id,
            project_id=doc["project_id"],
            artifact_type=task_type,
            model=res["model"],
            provider="openai_compatible",
            prompt_version="v1.0",
            result_json=res["result"],
            input_tokens=res.get("input_tokens", 0),
            output_tokens=res.get("output_tokens", 0),
            cost=res.get("cost", 0.0)
        )
        return {"id": art_id, **res}

# --- Site Quick Inspector (PRD Section 65) ---
@app.post("/api/inspect-url")
async def inspect_url(data: Dict[str, str] = Body(...)):
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")

    is_safe, err_msg = is_safe_url(url)
    if not is_safe:
        return {"success": False, "error": f"安全拦截: {err_msg}"}

    fetcher = HttpFetcher(timeout_seconds=10)
    try:
        res = await fetcher.fetch(url)
        if res.status_code == 0:
            return {"success": False, "error": res.error or "Failed to connect"}

        from engine.fetcher.smart_fetcher import is_spa_or_empty_content
        needs_js = is_spa_or_empty_content(res.text)

        extractor = GenericArticleExtractor()
        extracted = extractor.extract(res.text, url)

        # Check sitemap or RSS
        website_ext = GenericWebsiteExtractor()
        site_info = website_ext.extract(res.text, url)

        return {
            "success": True,
            "url": res.url,
            "status_code": res.status_code,
            "response_time_ms": res.response_time_ms,
            "title": extracted.title,
            "author": extracted.author,
            "detected_type": "Article" if len(extracted.text) > 300 else "Website/SPA",
            "needs_browser": needs_js,
            "feed_count": len(site_info.metadata.get("feeds", [])),
            "discovered_links_sample": extracted.links[:10],
            "total_links_found": len(extracted.links)
        }
    finally:
        await fetcher.close()

# --- Export ---
@app.post("/api/projects/{project_id}/export")
def export_project(project_id: str, format: str = Body("markdown"), doc_ids: Optional[List[str]] = Body(None)):
    with get_db() as conn:
        repo = Repository(conn)
        service = ExportService(repo)
        path = service.export_project(project_id, format_type=format, doc_ids=doc_ids)
        return {"success": True, "export_path": path, "format": format}

# --- Settings & Costs ---
@app.get("/api/settings")
def get_settings():
    settings = load_settings()
    ai_settings = settings.get("ai", {})
    api_key = ai_settings.get("api_key") or os.getenv("OPENAI_API_KEY", "")
    base_url = ai_settings.get("base_url") or os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    model = ai_settings.get("model") or os.getenv("OPENAI_MODEL", "deepseek-chat")
    crawler_settings = settings.get("crawler", {})

    asr_settings = settings.get("asr", {})

    return {
        "ai": {
            "api_key_set": bool(api_key),
            "base_url": base_url,
            "model": model
        },
        "crawler": {
            "default_user_agent": crawler_settings.get("default_user_agent", DEFAULT_USER_AGENT),
            "default_preset": crawler_settings.get("default_preset", "balanced")
        },
        "asr": {
            "enabled": asr_settings.get("enabled", False),
            "mode": asr_settings.get("mode", "remote"),
            "model_size": asr_settings.get("model_size", "base"),
            "device": asr_settings.get("device", "cpu"),
            "remote_base_url": asr_settings.get("remote_base_url", "https://api.openai.com/v1"),
            "remote_api_key_set": bool(asr_settings.get("remote_api_key")),
            "remote_model": asr_settings.get("remote_model", "whisper-1")
        }
    }

@app.post("/api/settings")
def update_settings(data: Dict[str, Any] = Body(...)):
    global ai_client, ai_worker
    save_settings(data)

    settings = load_settings()
    ai_settings = settings.get("ai", {})
    api_key = ai_settings.get("api_key") or os.getenv("OPENAI_API_KEY")
    base_url = ai_settings.get("base_url") or os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    model = ai_settings.get("model") or os.getenv("OPENAI_MODEL", "deepseek-chat")

    if api_key:
        ai_client = AIProviderClient(api_key=api_key, base_url=base_url, default_model=model)
        if ai_worker:
            ai_worker.ai_client = ai_client

    return {"status": "updated"}

@app.get("/api/projects/{project_id}/costs")
def get_project_costs(project_id: str):
    with get_db() as conn:
        repo = Repository(conn)
        return repo.get_project_ai_cost(project_id)

# --- Plugins & Rule Adapters (PRD Section 24-30, 81-82, 103) ---
from engine.extractors.plugin_manager import plugin_manager

@app.get("/api/plugins")
def list_plugins():
    return plugin_manager.list_plugins()

@app.post("/api/plugins")
def create_plugin(data: Dict[str, Any] = Body(...)):
    return plugin_manager.create_or_update_rule_plugin(data)

@app.post("/api/plugins/{plugin_id}/toggle")
def toggle_plugin(plugin_id: str, data: Dict[str, Any] = Body(...)):
    enabled = data.get("enabled", True)
    plugin_manager.toggle_plugin(plugin_id, enabled)
    return {"status": "ok", "enabled": enabled}

@app.delete("/api/plugins/{plugin_id}")
def delete_plugin(plugin_id: str):
    try:
        plugin_manager.delete_plugin(plugin_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/plugins/test-rule")
async def test_rule(data: Dict[str, Any] = Body(...)):
    url = data.get("url")
    rules = data.get("rules", {})
    html = data.get("html")
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")
    if not html:
        is_safe, err_msg = is_safe_url(url)
        if not is_safe:
            return {"success": False, "error": f"安全拦截: {err_msg}"}
    return await plugin_manager.test_rule_online(url=url, rules=rules, html=html)

@app.post("/api/plugins/{plugin_id}/diagnose-repair")
async def diagnose_plugin_repair(plugin_id: str, data: Dict[str, Any] = Body(...)):
    url = data.get("url")
    html = data.get("html")
    if not url:
        raise HTTPException(status_code=400, detail="Missing url")

    # Find target plugin
    plugins = plugin_manager.list_plugins()
    target = next((p for p in plugins if p["id"] == plugin_id), None)
    if not target or not target.get("rules"):
        raise HTTPException(status_code=404, detail="Plugin not found or does not have CSS rules.")

    if not html:
        is_safe, err_msg = is_safe_url(url)
        if not is_safe:
            return {"success": False, "error": f"安全拦截: {err_msg}"}
        from engine.fetcher.http_fetcher import HttpFetcher
        fetcher = HttpFetcher(timeout_seconds=12)
        try:
            res = await fetcher.fetch(url)
            if res.status_code == 0 or not res.text:
                return {"success": False, "error": res.error or f"无法获取页面 {url}"}
            html = res.text
        finally:
            await fetcher.close()

    from engine.ai.selector_repair import diagnose_and_repair_selectors
    return await diagnose_and_repair_selectors(
        url=url,
        html=html,
        rules=target["rules"],
        ai_client=ai_client
    )

@app.post("/api/plugins/{plugin_id}/apply-repair")
def apply_plugin_repair(plugin_id: str, data: Dict[str, Any] = Body(...)):
    suggested_rules = data.get("suggested_rules")
    if not suggested_rules or not isinstance(suggested_rules, dict):
        raise HTTPException(status_code=400, detail="Invalid suggested_rules")
    try:
        updated = plugin_manager.apply_selector_repair(plugin_id, suggested_rules)
        return {"success": True, "plugin": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/plugins/presets")
def list_preset_plugins():
    """List bundled high-value website rule presets (PRD Section 81, 114)."""
    from engine.extractors.preset_plugins import get_preset_plugins
    return get_preset_plugins()

@app.post("/api/plugins/presets/{preset_id}/install")
def install_preset_plugin(preset_id: str):
    """Install a bundled preset plugin into custom rule plugins."""
    from engine.extractors.preset_plugins import get_preset_plugins
    presets = get_preset_plugins()
    target = next((p for p in presets if p["id"] == preset_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Preset plugin not found")
    installed = plugin_manager.create_or_update_rule_plugin(target)
    return {"success": True, "plugin": installed}

@app.get("/api/plugins/{plugin_id}/export")
def export_plugin(plugin_id: str):
    """Export plugin configuration to JSON schema (PRD Section 81)."""
    plugins = plugin_manager.list_plugins()
    target = next((p for p in plugins if p["id"] == plugin_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return target

@app.post("/api/plugins/import")
def import_plugin(data: Dict[str, Any] = Body(...)):
    """Import and validate external plugin rules (PRD Section 25, 82)."""
    from engine.extractors.preset_plugins import validate_and_parse_plugin_data
    try:
        validated = validate_and_parse_plugin_data(data)
        installed = plugin_manager.create_or_update_rule_plugin(validated)
        return {"success": True, "plugin": installed}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Website Monitoring (PRD Section 75-77, 104) ---

@app.get("/api/monitoring/schedules")
def list_monitor_schedules(project_id: Optional[str] = None):
    with get_db() as conn:
        repo = Repository(conn)
        return repo.list_monitor_schedules(project_id)

@app.post("/api/monitoring/schedules")
def create_monitor_schedule(data: Dict[str, Any] = Body(...)):
    with get_db() as conn:
        repo = Repository(conn)
        return repo.create_monitor_schedule(
            project_id=data["project_id"],
            name=data["name"],
            url=data["url"],
            interval_minutes=int(data.get("interval_minutes", 60)),
            target_id=data.get("target_id"),
            schedule_type=data.get("schedule_type", "interval"),
            cron_expression=data.get("cron_expression")
        )

@app.post("/api/monitoring/validate-cron")
def validate_cron_endpoint(data: Dict[str, Any] = Body(...)):
    expr = data.get("expression", "").strip()
    from engine.scheduler.cron_parser import CronParser
    valid, msg = CronParser.validate_cron(expr)
    if not valid:
        return {"valid": False, "error": msg}
    desc = CronParser.describe_cron(expr)
    next_runs = [d.strftime("%Y-%m-%d %H:%M:%S") for d in CronParser.get_next_n_runs(expr, 5)]
    return {
        "valid": True,
        "description": desc,
        "next_runs": next_runs
    }

@app.post("/api/monitoring/schedules/{schedule_id}/toggle")
def toggle_monitor_schedule(schedule_id: str, data: Dict[str, Any] = Body(...)):
    with get_db() as conn:
        repo = Repository(conn)
        repo.toggle_monitor_schedule(schedule_id, data.get("enabled", True))
        return {"status": "ok"}

@app.delete("/api/monitoring/schedules/{schedule_id}")
def delete_monitor_schedule(schedule_id: str):
    with get_db() as conn:
        repo = Repository(conn)
        repo.delete_monitor_schedule(schedule_id)
        return {"success": True}

@app.get("/api/monitoring/events")
def list_monitor_events(project_id: Optional[str] = None, limit: int = 50):
    with get_db() as conn:
        repo = Repository(conn)
        return repo.list_monitor_events(project_id=project_id, limit=limit)

# --- Document Diff (PRD Section 73) ---
from engine.utils.diff_helper import compute_text_diff

@app.get("/api/documents/{document_id}/diff")
def get_document_diff(document_id: str):
    with get_db() as conn:
        repo = Repository(conn)
        doc = repo.get_document(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        history = repo.get_document_snapshots_history(document_id)
        if len(history) < 2:
            return {
                "has_diff": False,
                "message": "该文档仅有一次抓取记录，无历史对比快照。",
                "diff_lines": []
            }

        # Compare current snapshot with the previous snapshot
        current_text = doc["text"] or doc["markdown"]
        prev_snap = history[1]
        prev_doc_id = prev_snap.get("doc_id")
        prev_text = ""
        if prev_doc_id:
            prev_doc = repo.get_document(prev_doc_id)
            if prev_doc:
                prev_text = prev_doc["text"] or prev_doc["markdown"]

        diff_lines = compute_text_diff(prev_text, current_text)
        return {
            "has_diff": True,
            "previous_date": prev_snap.get("fetched_at"),
            "current_date": history[0].get("fetched_at"),
            "diff_lines": diff_lines
        }

# --- Project AI Synthesis Report (PRD Section 43-44, 97) ---
@app.post("/api/projects/{project_id}/generate-report")
async def generate_project_report(project_id: str, model: Optional[str] = Body(None)):
    global ai_client
    if not ai_client:
        raise HTTPException(status_code=400, detail="AI Provider is not configured. Please set API Key in settings.")

    with get_db() as conn:
        repo = Repository(conn)
        proj = repo.get_project(project_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

        docs, total = repo.list_documents(project_id, limit=30)
        if not docs:
            raise HTTPException(status_code=400, detail="该项目下暂无已归档文档，无法生成综合研报。")

        # Compile summaries
        summary_lines = []
        for idx, d in enumerate(docs):
            summary_lines.append(f"### 文档 {idx+1}: {d['title']}\n来源: {d['url']}\n摘要/要点: {(d['text'] or d['markdown'])[:600]}...\n")

        compiled_content = "\n".join(summary_lines)

    res = await ai_client.execute_task(
        task_type="project_report_v1",
        content=compiled_content,
        title=proj["name"],
        model=model
    )

    if "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])

    with get_db() as conn:
        repo = Repository(conn)
        art_id = repo.create_ai_artifact(
            document_id=docs[0]["id"],
            project_id=project_id,
            artifact_type="project_report_v1",
            model=res["model"],
            provider="openai_compatible",
            prompt_version="v1.0",
            result_json=res["result"],
            input_tokens=res.get("input_tokens", 0),
            output_tokens=res.get("output_tokens", 0),
            cost=res.get("cost", 0.0)
        )

    return {"id": art_id, **res}

# --- Autonomous Research Agent Loop (PRD Section 49 & 105) ---
from engine.ai.research_agent import research_manager

@app.post("/api/research/start")
def start_research_task(data: Dict[str, Any] = Body(...)):
    project_id = data.get("project_id")
    topic = data.get("topic", "").strip()
    if not project_id or not topic:
        raise HTTPException(status_code=400, detail="Missing project_id or topic")

    max_pages = int(data.get("max_pages", 5))
    max_rounds = int(data.get("max_rounds", 3))
    min_relevance = int(data.get("min_relevance", 60))

    task = research_manager.start_task(
        project_id=project_id,
        topic=topic,
        max_pages=max_pages,
        max_rounds=max_rounds,
        min_relevance=min_relevance,
        ai_client=ai_client
    )
    return task.to_dict()

@app.get("/api/research/tasks")
def list_research_tasks(project_id: Optional[str] = None):
    return research_manager.list_tasks(project_id=project_id)

@app.get("/api/research/tasks/{task_id}")
def get_research_task(task_id: str):
    task = research_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Research task not found")
    return task.to_dict()

@app.post("/api/research/tasks/{task_id}/stop")
def stop_research_task(task_id: str):
    success = research_manager.stop_task(task_id)
    return {"success": success}

# --- Storage Policy & Cache Clean (PRD Section 91-92) ---
@app.post("/api/storage/clear-cache")
def clear_cache():
    with get_db() as conn:
        conn.execute("DELETE FROM ai_cache;")
    return {"success": True, "message": "AI 缓存已清空"}

# --- WebSocket Stream ---
@app.websocket("/ws/crawls/{job_id}")
async def ws_crawl_monitor(websocket: WebSocket, job_id: str):
    await event_bus.register(websocket, job_id)
    try:
        while True:
            # Keepalive listener
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        await event_bus.unregister(websocket, job_id)
    except Exception:
        await event_bus.unregister(websocket, job_id)

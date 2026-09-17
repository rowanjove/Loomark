import os
import tempfile
import pytest
from pathlib import Path

from engine.db.session import init_db, get_db
from engine.db.repository import Repository
from engine.utils.diff_helper import compute_text_diff
from engine.extractors.plugin_manager import PluginManager
from engine.extractors.media_subtitle import parse_vtt_or_srv_text, postprocess_subtitles
from engine.ai.chunker import split_text_into_chunks
from engine.ai.prompts import PROMPT_TEMPLATES
from engine.fetcher.base import BaseFetcher, FetchResult
from engine.fetcher.smart_fetcher import SmartFetcher

def test_diff_helper():
    old_text = "Line 1: Intro\nLine 2: Section A\nLine 3: Section B"
    new_text = "Line 1: Intro\nLine 2: Section A (Modified)\nLine 3: Section B\nLine 4: Conclusion"

    diff = compute_text_diff(old_text, new_text)
    assert len(diff) > 0
    # Should have equal, delete, insert types
    types = [d["type"] for d in diff]
    assert "equal" in types
    assert "insert" in types
    assert any("Conclusion" in d["text"] for d in diff)

def test_chunker():
    long_text = ("This is a paragraph about AI crawlers and knowledge engines. " * 30 + "\n\n") * 10
    chunks = split_text_into_chunks(long_text, max_chunk_chars=1000)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c["text"]) <= 1200
        assert "chunk_index" in c
        assert c["token_count"] > 0

def test_subtitles_parser_and_cleaner():
    sample_vtt = """WEBVTT

00:00:01.000 --> 00:00:03.500
Hello and welcome to Loomark.

00:00:03.500 --> 00:00:04.200
Hello and welcome to Loomark.

00:00:04.500 --> 00:00:05.100
Let's

00:00:05.150 --> 00:00:07.000
get started with web intelligence.
"""
    segments = parse_vtt_or_srv_text(sample_vtt)
    assert len(segments) >= 3

    # Postprocessing should deduplicate consecutive duplicate lines
    cleaned = postprocess_subtitles(segments)
    # Consecutive "Hello and welcome to Loomark." should be merged
    greeting_count = sum(1 for s in cleaned if "Hello and welcome to Loomark" in s["text"])
    assert greeting_count == 1
    # Short fragments "Let's" and "get started..." should be merged
    assert any("Let's get started" in s["text"] for s in cleaned)

def test_plugin_manager(tmp_path):
    pm = PluginManager(plugins_dir=tmp_path)
    plugins = pm.list_plugins()
    assert len(plugins) >= 3 # at least builtins

    # Create custom rule plugin
    created = pm.create_or_update_rule_plugin({
        "id": "tech_blog_rule",
        "name": "Tech Blog Custom Rule",
        "match": ["techblog.io", "*.techblog.io"],
        "rules": {
            "title": "h1.post-heading",
            "content": "article.post-body",
            "author": ".author-tag"
        }
    })
    assert created["id"] == "tech_blog_rule"
    assert (tmp_path / "tech_blog_rule" / "manifest.json").exists()

    # Find matching extractor
    extractor = pm.find_matching_extractor("https://sub.techblog.io/article/1")
    assert extractor is not None

    non_matching = pm.find_matching_extractor("https://otherdomain.com/article/1")
    assert non_matching is None

    # Test online rule extraction
    html = """
    <html><body>
        <h1 class="post-heading">My Custom Tech Article</h1>
        <div class="author-tag">Dr. Alice</div>
        <article class="post-body">
            <p>Here is the extracted content using CSS rules.</p>
        </article>
    </body></html>
    """
    import asyncio
    test_res = asyncio.run(pm.test_rule_online(
        url="https://sub.techblog.io/article/1",
        rules={
            "title": "h1.post-heading",
            "content": "article.post-body",
            "author": ".author-tag"
        },
        html=html
    ))
    assert test_res["success"] is True
    assert test_res["title"] == "My Custom Tech Article"
    assert "Dr. Alice" in test_res["author"]
    assert "extracted content" in test_res["text_preview"]

def test_monitoring_repository():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = Path(tf.name)

    try:
        init_db(db_path)
        with get_db(db_path) as conn:
            repo = Repository(conn)
            proj = repo.create_project("Monitor Test Project")
            pid = proj["id"]

            # Create schedule
            sched = repo.create_monitor_schedule(
                project_id=pid,
                name="Daily Competitor Check",
                url="https://example.com/pricing",
                interval_minutes=60
            )
            assert sched["name"] == "Daily Competitor Check"
            assert sched["enabled"] == 1

            # Get due schedules
            due = repo.get_due_monitor_schedules()
            assert any(s["id"] == sched["id"] for s in due)

            # Record change event
            event_id = repo.create_monitor_event(
                project_id=pid,
                schedule_id=sched["id"],
                url="https://example.com/pricing",
                event_type="UPDATED",
                old_content_hash="hash_old",
                new_content_hash="hash_new",
                ai_change_summary="产品价格由 $99 上调至 $129。"
            )
            assert event_id is not None

            # List events
            events = repo.list_monitor_events(pid)
            assert len(events) == 1
            assert events[0]["event_type"] == "UPDATED"
            assert "价格" in events[0]["ai_change_summary"]
    finally:
        if db_path.exists():
            try:
                os.remove(db_path)
            except Exception:
                pass

@pytest.mark.asyncio
async def test_smart_fetcher_browser_fallback():
    class MockHttpFetcher(BaseFetcher):
        async def fetch(self, url: str, **kwargs):
            # Returns empty SPA skeleton
            return FetchResult(
                url=url,
                status_code=200,
                text="<html><body><div id='app'></div><script src='/bundle.js'></script></body></html>",
                raw_bytes=b"dummy",
                response_time_ms=10
            )
        async def close(self):
            pass

    class MockBrowserFetcher(BaseFetcher):
        async def fetch(self, url: str, **kwargs):
            # Returns rendered SPA content
            return FetchResult(
                url=url,
                status_code=200,
                text="<html><body><div id='app'><h1>Rendered Vue SPA</h1><p>Dynamic Content</p></div></body></html>",
                raw_bytes=b"rendered",
                response_time_ms=500,
                is_browser_rendered=True
            )
        async def close(self):
            pass

    smart = SmartFetcher(http_fetcher=MockHttpFetcher(), browser_fetcher=MockBrowserFetcher())
    res = await smart.fetch("https://spa-example.com")
    assert res.is_browser_rendered is True
    assert "Rendered Vue SPA" in res.text
    await smart.close()

def test_new_prompt_templates():
    assert "entity_extraction_v1" in PROMPT_TEMPLATES
    assert "project_report_v1" in PROMPT_TEMPLATES
    assert "persons" in PROMPT_TEMPLATES["entity_extraction_v1"]["system"]
    assert "综合研究分析报告" in PROMPT_TEMPLATES["project_report_v1"]["system"]

def test_deep_merge_settings_protection():
    from engine.config import deep_merge
    base = {
        "ai": {"api_key": "sk-secret-123", "model": "deepseek-chat"},
        "crawler": {"default_preset": "balanced"}
    }
    incoming = {
        "ai": {"base_url": "https://new-url.com/v1"},
        "crawler": {"default_preset": "fast"}
    }
    result = deep_merge(base, incoming)
    assert result["ai"]["api_key"] == "sk-secret-123"
    assert result["ai"]["base_url"] == "https://new-url.com/v1"
    assert result["crawler"]["default_preset"] == "fast"

def test_plugin_security_hardening(tmp_path):
    from engine.extractors.plugin_manager import PluginManager
    pm = PluginManager(plugins_dir=tmp_path)

    plugin = pm.create_or_update_rule_plugin({
        "name": "中文自定义规则！@#￥%",
        "rules": {"title": "h1"}
    })
    assert plugin["id"].startswith("rule_")
    assert (tmp_path / plugin["id"] / "manifest.json").exists()

    with pytest.raises(ValueError):
        pm.delete_plugin("")

    with pytest.raises(ValueError):
        pm.delete_plugin("..")

    assert pm.delete_plugin(plugin["id"]) is True
    assert not (tmp_path / plugin["id"]).exists()
    assert tmp_path.exists()

def test_is_safe_url_ssrf_protection():
    from engine.frontier.normalizer import is_safe_url

    # Localhost and loopback
    safe, msg = is_safe_url("http://localhost:8080/admin")
    assert safe is False
    assert "本地回环" in msg

    safe, msg = is_safe_url("http://127.0.0.1:8765/api")
    assert safe is False
    assert "本地回环" in msg

    # Private RFC1918 subnets
    safe, msg = is_safe_url("http://192.168.1.1/router")
    assert safe is False
    assert "私有" in msg

    safe, msg = is_safe_url("http://10.0.0.5/api")
    assert safe is False
    assert "私有" in msg

    # Public valid URLs should pass
    safe, msg = is_safe_url("https://example.com/news")
    assert safe is True

def test_plugin_get_and_runner_rule_adapter(tmp_path):
    from engine.extractors.plugin_manager import PluginManager
    from engine.scheduler.manager import CrawlJobRunner
    from engine.extractors.json_rule_adapter import JsonRuleExtractor
    from engine.extractors.generic_article import GenericArticleExtractor

    pm = PluginManager(plugins_dir=tmp_path)
    p = pm.create_or_update_rule_plugin({
        "id": "test_blog_rule",
        "name": "Test Blog Rule",
        "rules": {"title": "h2.title", "content": "div.entry"}
    })

    # Test get_plugin
    found = pm.get_plugin("test_blog_rule")
    assert found is not None
    assert found["id"] == "test_blog_rule"
    assert pm.get_plugin("non_existent_plugin_xyz") is None

    # Test runner with rule: JSON string
    runner1 = CrawlJobRunner(
        job_id="job1",
        project_id="p1",
        config={"adapter_id": "rule:{\"title\":\"h1\",\"content\":\".post\"}"}
    )
    assert isinstance(runner1.extractor, JsonRuleExtractor)

    # Test runner with default article
    runner2 = CrawlJobRunner(
        job_id="job2",
        project_id="p1",
        config={"adapter_id": "article"}
    )
    assert isinstance(runner2.extractor, GenericArticleExtractor)




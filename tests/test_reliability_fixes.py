import asyncio
import json
import pytest
import tempfile
from pathlib import Path

from engine.frontier.rate_limiter import DomainRateLimiter
from engine.extractors.json_rule_adapter import JsonRuleExtractor
from engine.scheduler.manager import CrawlManager
from engine.db.session import init_db, get_db
from engine.db.repository import Repository
from engine.ai.client import AIProviderClient

@pytest.mark.asyncio
async def test_rate_limiter_cancellation_no_leak():
    """Verify that cancelling during polite delay does not leak semaphore slots."""
    limiter = DomainRateLimiter(domain_concurrent=1, domain_delay_ms=2000)

    # 1. First acquire sets _last_request_time
    await limiter.acquire("example.com")
    limiter.release("example.com")

    # 2. Start a task that acquires immediately; it will hit the 2000ms delay sleep
    async def doomed_task():
        await limiter.acquire("example.com")
        try:
            await asyncio.sleep(10)
        finally:
            limiter.release("example.com")

    task = asyncio.create_task(doomed_task())
    # Wait briefly for task to acquire semaphore and enter sleep(required_delay - elapsed)
    await asyncio.sleep(0.05)
    # Cancel the task while it is sleeping inside limiter.acquire
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # 3. Now verify semaphore was released on cancellation and can be acquired without hanging
    sem = await limiter._get_semaphore("example.com")
    assert sem.locked() is False, "Semaphore slot was leaked on cancellation!"

    # Acquire should succeed without timeout
    await asyncio.wait_for(limiter.acquire("example.com"), timeout=3.0)
    limiter.release("example.com")

@pytest.mark.asyncio
async def test_crawl_manager_restart_resume_recovery():
    """Verify CrawlManager can recover and resume a paused job from DB even if self.runners is empty."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = Path(tf.name)

    try:
        init_db(db_path)
        with get_db(db_path) as conn:
            repo = Repository(conn)
            proj = repo.create_project("Recovery Test")
            job = repo.create_crawl_job(
                project_id=proj["id"],
                name="Test Job to Recover",
                config={"preset": "gentle", "max_pages": 5}
            )
            job_id = job["id"]
            repo.update_job_status(job_id, "PAUSED")

        # Instantiate a fresh CrawlManager with empty runners (simulating app restart)
        manager = CrawlManager()
        assert job_id not in manager.runners

        # Patch get_db in manager module temporarily to point to our temp DB
        import engine.scheduler.manager as mgr_module
        orig_get_db = mgr_module.get_db
        mgr_module.get_db = lambda: get_db(db_path)

        try:
            runner = manager.resume_job(job_id)
            assert runner is not None, "Failed to recover runner from DB"
            assert job_id in manager.runners
            assert runner.is_paused is False
            assert runner.is_stopped is False

            # Verify DB status updated to RUNNING
            with get_db(db_path) as conn:
                updated_job = Repository(conn).get_crawl_job(job_id)
                assert updated_job["status"] == "RUNNING"

            # Clean up runner task
            manager.stop_job(job_id)
            with get_db(db_path) as conn:
                stopped_job = Repository(conn).get_crawl_job(job_id)
                assert stopped_job["status"] == "STOPPED"
        finally:
            mgr_module.get_db = orig_get_db
    finally:
        db_path.unlink(missing_ok=True)

def test_json_rule_extractor_invalid_css_syntax():
    """Verify invalid CSS selector syntax does not crash extraction."""
    invalid_rules = {
        "title": "h1:nth-child(unclosed",  # Invalid CSS selector
        "content": ".valid-content",
        "author": "span[invalid=unclosed",  # Invalid CSS selector
        "date": "time"
    }
    extractor = JsonRuleExtractor(invalid_rules)
    html = """
    <html>
        <body>
            <div class="valid-content">Valid Article Content Body Here.</div>
            <time datetime="2026-09-17">2026-09-17</time>
            <a href="/link1">Link 1</a>
        </body>
    </html>
    """
    # Should not raise SelectorSyntaxError
    result = extractor.extract(html, "https://example.com/post")
    assert result.title == "Untitled"  # Invalid selector skipped safely
    assert "Valid Article Content Body Here." in result.text
    assert result.published_at == "2026-09-17"
    assert len(result.links) == 1
    assert result.links[0] == "https://example.com/link1"

@pytest.mark.asyncio
async def test_ai_client_universal_json_parsing():
    """Verify universal parsing of Markdown JSON fences into result['data']."""
    client = AIProviderClient(api_key="mock", default_model="mock")

    # Mock chat completion response with markdown fences
    class MockChoice:
        def __init__(self, content):
            self.message = type("Msg", (), {"content": content})()

    class MockResponse:
        def __init__(self, content):
            self.choices = [MockChoice(content)]
            self.usage = type("Usage", (), {"prompt_tokens": 10, "completion_tokens": 20})()

    raw_json_str = '```json\n{\n  "persons": ["Alice", "Bob"],\n  "organizations": ["OpenAI"]\n}\n```'

    async def mock_create(**kwargs):
        return MockResponse(raw_json_str)

    client.client.chat.completions.create = mock_create

    # Test entity_extraction_v1
    res = await client.execute_task(
        task_type="entity_extraction_v1",
        content="Alice and Bob visited OpenAI today.",
        title="Sample"
    )

    assert "data" in res["result"]
    assert res["result"]["data"]["persons"] == ["Alice", "Bob"]
    assert res["result"]["data"]["organizations"] == ["OpenAI"]

def test_hybrid_search_no_drop():
    """Verify hybrid search does not drop documents returned by FTS."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = Path(tf.name)

    try:
        init_db(db_path)
        with get_db(db_path) as conn:
            repo = Repository(conn)
            proj = repo.create_project("Hybrid Test")
            proj_id = proj["id"]

            target = repo.create_target(proj_id, "https://test.com")
            job = repo.create_crawl_job(proj_id, "Job", {})

            url_data = repo.create_url(proj_id, "https://test.com/doc1", "https://test.com/doc1", "h1", "test.com", job_id=job["id"])
            snap_id = repo.create_snapshot(url_data["id"], job["id"], proj_id, 200, {}, None, "chash1")
            doc_id = repo.create_document(
                snapshot_id=snap_id,
                project_id=proj_id,
                url_id=url_data["id"],
                doc_type="article",
                title="UniqueQuantumKeyword Breakthrough",
                author="Scientist",
                published_at="2026-09-17",
                text="A major breakthrough in Quantum Computing with UniqueQuantumKeyword occurred.",
                markdown="Quantum Computing",
                language="en",
                metadata={},
                content_hash="chash1"
            )

            # Perform hybrid search
            results, total = repo.hybrid_search_documents(
                project_id=proj_id,
                query="UniqueQuantumKeyword",
                mode="hybrid"
            )

            assert total >= 1
            assert len(results) >= 1
            assert results[0]["id"] == doc_id
            assert "search_score" in results[0]
    finally:
        db_path.unlink(missing_ok=True)

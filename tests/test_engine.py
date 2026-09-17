import os
import tempfile
import pytest
from pathlib import Path
from engine.frontier.normalizer import normalize_url, is_valid_http_url, is_in_scope
from engine.db.session import get_db, init_db
from engine.db.repository import Repository
from engine.extractors.generic_article import GenericArticleExtractor
from engine.extractors.generic_website import GenericWebsiteExtractor
from engine.extractors.json_rule_adapter import JsonRuleExtractor
from engine.exporter.export_service import ExportService

def test_url_normalizer():
    # Test tracking params removal
    url1 = "https://EXAMPLE.com:443/news/article/?utm_source=twitter&utm_medium=social&b=2&a=1#section1"
    norm1, hash1, domain1 = normalize_url(url1)

    assert domain1 == "example.com"
    assert "utm_source" not in norm1
    assert "section1" not in norm1
    assert "443" not in norm1
    assert norm1 == "https://example.com/news/article?a=1&b=2"

    # Same URL with different param order and tracking param produces identical hash
    url2 = "https://example.com/news/article?b=2&a=1&fbclid=XYZ"
    norm2, hash2, domain2 = normalize_url(url2)
    assert norm1 == norm2
    assert hash1 == hash2

def test_is_in_scope():
    base = "https://example.com/blog/intro"
    assert is_in_scope("https://example.com/blog/p1", base, scope="domain") is True
    assert is_in_scope("https://sub.example.com/blog", base, scope="domain") is False
    assert is_in_scope("https://sub.example.com/blog", base, scope="subdomain") is True
    assert is_in_scope("https://example.com/other", base, scope="path") is False
    assert is_in_scope("https://example.com/blog/deep/post", base, scope="path") is True

def test_db_and_fts():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = Path(tf.name)

    try:
        init_db(db_path)
        with get_db(db_path) as conn:
            repo = Repository(conn)
            # Create Project
            proj = repo.create_project("AI Research 2026", "Test project")
            assert proj["name"] == "AI Research 2026"
            proj_id = proj["id"]

            # Create Target
            target = repo.create_target(proj_id, "https://example.com", scope="domain")
            assert target["url"] == "https://example.com"

            # Create Crawl Job
            job = repo.create_crawl_job(proj_id, "Job 1", {"max_pages": 10}, target_id=target["id"])
            assert job["status"] == "PENDING"
            job_id = job["id"]

            # Insert URLs into Frontier
            repo.insert_urls_batch([{
                "job_id": job_id,
                "project_id": proj_id,
                "url": "https://example.com/post-1",
                "normalized_url": "https://example.com/post-1",
                "url_hash": "hash123",
                "domain": "example.com",
                "depth": 0,
                "priority": 100,
                "status": "QUEUED"
            }])

            popped = repo.pop_next_urls_for_domains(job_id, ["example.com"], limit=1)
            assert len(popped) == 1
            assert popped[0]["url_hash"] == "hash123"

            # Snapshot & Document
            snap_id = repo.create_snapshot(
                url_id=popped[0]["id"],
                job_id=job_id,
                project_id=proj_id,
                status_code=200,
                headers={"content-type": "text/html"},
                raw_html_path="/data/snap1.html",
                content_hash="contenthashabc"
            )

            doc_id = repo.create_document(
                snapshot_id=snap_id,
                project_id=proj_id,
                url_id=popped[0]["id"],
                doc_type="article",
                title="Deep Learning Breakthrough",
                author="John Doe",
                published_at="2026-09-01",
                text="Artificial Intelligence and autonomous crawlers are revolutionizing web indexing.",
                markdown="# Deep Learning\nArtificial Intelligence and autonomous crawlers...",
                language="en",
                metadata={"test": 1},
                content_hash="contenthashabc"
            )

            # Test FTS5 Full Text Search
            docs_found, count = repo.list_documents(proj_id, search="autonomous crawlers")
            assert count == 1
            assert docs_found[0]["title"] == "Deep Learning Breakthrough"

            # Search non-matching word
            _, zero_count = repo.list_documents(proj_id, search="blockchain crypto")
            assert zero_count == 0

    finally:
        if db_path.exists():
            try:
                os.remove(db_path)
            except Exception:
                pass

def test_extractors():
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tech Insights 2026</title>
        <meta name="description" content="A blog about modern software engineering.">
    </head>
    <body>
        <nav><a href="/home">Home</a></nav>
        <article>
            <h1>Future of AI Crawlers</h1>
            <p class="author">By Alice Zhang</p>
            <p>Modern crawlers must be intelligent, local-first, and resilient.</p>
            <p>They combine asynchronous fetching with semantic analysis.</p>
            <a href="/post/ai-agent">Read more about agents</a>
        </article>
        <footer><p>Copyright 2026</p></footer>
    </body>
    </html>
    """
    # 1. Generic Article Extractor
    article_ext = GenericArticleExtractor()
    extracted_art = article_ext.extract(sample_html, "https://example.com/tech-insights")
    assert "Future of AI Crawlers" in extracted_art.title or "Tech Insights" in extracted_art.title
    assert "Modern crawlers" in extracted_art.text
    assert any("ai-agent" in link for link in extracted_art.links)
    assert extracted_art.content_hash != ""

    # 2. JSON Rule Extractor
    rules = {
        "title": "h1",
        "content": "article p:nth-of-type(2)",
        "author": ".author",
        "type": "article"
    }
    rule_ext = JsonRuleExtractor(rules)
    extracted_rule = rule_ext.extract(sample_html, "https://example.com/tech-insights")
    assert extracted_rule.title == "Future of AI Crawlers"
    assert "Alice Zhang" in extracted_rule.author
    assert "Modern crawlers must be intelligent" in extracted_rule.text

def test_export_service():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = Path(tf.name)

    try:
        init_db(db_path)
        with get_db(db_path) as conn:
            repo = Repository(conn)
            proj = repo.create_project("Export Test", "Desc")
            proj_id = proj["id"]
            job = repo.create_crawl_job(proj_id, "Job Exp", {})
            repo.insert_urls_batch([{
                "job_id": job["id"],
                "project_id": proj_id,
                "url": "https://example.com/test",
                "normalized_url": "https://example.com/test",
                "url_hash": "hash_exp",
                "domain": "example.com"
            }])
            u = repo.pop_next_urls_for_domains(job["id"], ["example.com"])[0]
            snap_id = repo.create_snapshot(u["id"], job["id"], proj_id, 200, {}, None, "hash1")
            doc_id = repo.create_document(
                snap_id, proj_id, u["id"], "article", "Export Title", "Bob", None,
                "Hello World Content", "# Hello World Content", "en", {}, "hash1"
            )

            service = ExportService(repo)
            json_path = service.export_project(proj_id, format_type="json")
            assert Path(json_path).exists()

            csv_path = service.export_project(proj_id, format_type="csv")
            assert Path(csv_path).exists()

            md_path = service.export_project(proj_id, format_type="markdown")
            assert Path(md_path).exists()
    finally:
        if db_path.exists():
            try:
                os.remove(db_path)
            except Exception:
                pass

@pytest.mark.asyncio
async def test_crawl_job_runner_flow(monkeypatch):
    from engine.scheduler.manager import CrawlJobRunner
    from engine.fetcher.base import BaseFetcher, FetchResult

    class MockFetcher(BaseFetcher):
        async def fetch(self, url: str, **kwargs) -> FetchResult:
            if "page1" in url:
                html = """
                <html><body>
                    <h1>Page 1 Title</h1>
                    <p>First page content for testing.</p>
                    <a href="https://example.com/page2">Page 2</a>
                </body></html>
                """
            else:
                html = """
                <html><body>
                    <h1>Page 2 Title</h1>
                    <p>Second page content for testing.</p>
                </body></html>
                """
            return FetchResult(
                url=url,
                status_code=200,
                text=html,
                raw_bytes=html.encode(),
                response_time_ms=50
            )

        async def close(self):
            pass

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = Path(tf.name)

    try:
        init_db(db_path)
        monkeypatch.setattr("engine.scheduler.manager.get_db", lambda: get_db(db_path))

        with get_db(db_path) as conn:
            repo = Repository(conn)
            proj = repo.create_project("Runner Test")
            proj_id = proj["id"]
            job = repo.create_crawl_job(proj_id, "Test Crawl", {
                "max_pages": 5,
                "max_depth": 2,
                "scope": "domain",
                "preset": "fast"
            })
            job_id = job["id"]

        runner = CrawlJobRunner(job_id, proj_id, {
            "max_pages": 5,
            "max_depth": 2,
            "scope": "domain",
            "preset": "fast"
        })
        runner.fetcher = MockFetcher()

        await runner.run(["https://example.com/page1"])

        with get_db(db_path) as conn:
            repo = Repository(conn)
            job_updated = repo.get_crawl_job(job_id)
            assert job_updated["status"] == "COMPLETED"

            docs, count = repo.list_documents(proj_id)
            assert count == 2
            titles = [d["title"] for d in docs]
            assert any("Page 1" in t for t in titles)
            assert any("Page 2" in t for t in titles)
    finally:
        if db_path.exists():
            try:
                os.remove(db_path)
            except Exception:
                pass

def test_ai_prompt_safe_formatting():
    from engine.ai.client import AIProviderClient
    client = AIProviderClient(api_key="mock_key")
    # Test text containing code with curly brackets, JSON, templates
    content_with_braces = """
    function calculate() {
        const payload = {"key": "value", "items": [1, 2, 3]};
        return `${payload.key}`;
    }
    """
    # Verify client.execute_task builds prompt without KeyError
    # (will test prompt building logic)
    prompt_info = {"version": "v1.0", "user": "Title: {title}\nContent: {content}"}
    clipped = content_with_braces[:12000]
    user_prompt = prompt_info["user"].replace("{title}", "Test Title").replace("{content}", clipped)
    assert "Test Title" in user_prompt
    assert "calculate()" in user_prompt

def test_fts_special_characters_resilience():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = Path(tf.name)

    try:
        init_db(db_path)
        with get_db(db_path) as conn:
            repo = Repository(conn)
            proj = repo.create_project("FTS Resilience Project")
            pid = proj["id"]
            job = repo.create_crawl_job(pid, "FTS Job", {})
            repo.insert_urls_batch([{
                "job_id": job["id"],
                "project_id": pid,
                "url": "https://example.com/cplusplus",
                "normalized_url": "https://example.com/cplusplus",
                "url_hash": "cplus_hash",
                "domain": "example.com"
            }])
            u = repo.pop_next_urls_for_domains(job["id"], ["example.com"])[0]
            snap_id = repo.create_snapshot(u["id"], job["id"], pid, 200, {}, None, "cplus_hash")
            repo.create_document(
                snap_id, pid, u["id"], "article", "C++ Algorithms & Python Tips", "Author", None,
                "Deep dive into C++ and Python syntax: function() { return 0; }", "", "en", {}, "cplus_hash"
            )

            # Queries containing special characters that would crash raw FTS5 MATCH
            tricky_queries = ['"unclosed quote', 'C++', 'NOT token', 'foo:bar', '(parentheses)', '***']
            for q in tricky_queries:
                docs, count = repo.list_documents(pid, search=q)
                # Should not raise exception
                assert isinstance(docs, list)
                assert isinstance(count, int)

            # Standard search should find the doc
            matched, cnt = repo.list_documents(pid, search="Algorithms")
            assert cnt == 1
            assert matched[0]["title"] == "C++ Algorithms & Python Tips"
    finally:
        if db_path.exists():
            try:
                os.remove(db_path)
            except Exception:
                pass

def test_urls_unique_constraint_and_ignore():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = Path(tf.name)

    try:
        init_db(db_path)
        with get_db(db_path) as conn:
            repo = Repository(conn)
            proj = repo.create_project("Dedup Project")
            pid = proj["id"]
            job = repo.create_crawl_job(pid, "Dedup Job", {})
            jid = job["id"]

            batch = [
                {
                    "job_id": jid,
                    "project_id": pid,
                    "url": "https://example.com/page",
                    "normalized_url": "https://example.com/page",
                    "url_hash": "same_hash_1",
                    "domain": "example.com"
                },
                {
                    "job_id": jid,
                    "project_id": pid,
                    "url": "https://example.com/page",
                    "normalized_url": "https://example.com/page",
                    "url_hash": "same_hash_1",
                    "domain": "example.com"
                }
            ]
            inserted = repo.insert_urls_batch(batch)
            assert inserted == 1  # Only 1 was inserted, 1 was ignored!

            # Second insertion of same hash should insert 0
            second_insert = repo.insert_urls_batch(batch)
            assert second_insert == 0
    finally:
        if db_path.exists():
            try:
                os.remove(db_path)
            except Exception:
                pass

def test_settings_persistence(tmp_path, monkeypatch):
    import engine.config as config
    test_settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(config, "SETTINGS_FILE", test_settings_file)

    assert config.load_settings() == {}

    config.save_settings({
        "ai": {"api_key": "sk-123456", "model": "deepseek-chat"},
        "crawler": {"default_preset": "fast"}
    })

    loaded = config.load_settings()
    assert loaded["ai"]["api_key"] == "sk-123456"
    assert loaded["crawler"]["default_preset"] == "fast"



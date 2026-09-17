import pytest
from engine.ai.chunker import split_text_into_chunks, process_and_save_chunks
from engine.db.session import get_db, init_db
from engine.db.repository import Repository

def test_split_text_into_chunks():
    short_text = "这是一篇很短的内容，不需要分块。"
    chunks = split_text_into_chunks(short_text, max_chunk_chars=100)
    assert len(chunks) == 1
    assert chunks[0]["chunk_index"] == 0

    long_text = "\n\n".join([f"第 {i} 段内容：人工智能技术正在深刻改变软件开发范式。" * 5 for i in range(20)])
    chunks = split_text_into_chunks(long_text, max_chunk_chars=300)
    assert len(chunks) > 1
    for idx, c in enumerate(chunks):
        assert c["chunk_index"] == idx
        assert c["char_count"] > 0
        assert c["token_count"] > 0

def test_process_and_save_chunks(tmp_path):
    db_file = tmp_path / "test_chunks.db"
    init_db(db_file)
    with get_db(db_file) as conn:
        repo = Repository(conn)
        proj = repo.create_project("Chunk测试", "")
        proj_id = proj["id"]
        target = repo.create_target(proj_id, "https://example.com")
        target_id = target["id"]
        job = repo.create_crawl_job(proj_id, "Job 1", {}, target_id=target_id)
        job_id = job["id"]

        u_obj = repo.create_url(project_id=proj_id, url="https://example.com/long-doc", normalized_url="https://example.com/long-doc", url_hash="hash_chunk_url", domain="example.com", job_id=job_id)
        u = u_obj["id"]
        s = repo.create_snapshot(url_id=u, job_id=job_id, project_id=proj_id, status_code=200, headers={}, raw_html_path="raw_chunk.html", content_hash="hash_chunk")
        doc_id = repo.create_document(
            snapshot_id=s, project_id=proj_id, url_id=u, doc_type="article",
            title="超长技术白皮书", author="架构师", published_at="2026-09-01",
            text="第一段\n\n第二段\n\n第三段\n\n第四段", markdown="",
            language="zh", metadata={}, content_hash="hash_chunk"
        )



        saved = process_and_save_chunks(repo, doc_id, proj_id, "第一段：分布式系统。\n\n第二段：一致性协议。\n\n第三段：存储引擎。\n\n第四段：网络拓扑。", max_chunk_chars=25)
        assert len(saved) >= 2

        # Verify from database
        db_chunks = repo.get_document_chunks(doc_id)
        assert len(db_chunks) == len(saved)
        assert db_chunks[0]["document_id"] == doc_id
        assert db_chunks[0]["chunk_index"] == 0

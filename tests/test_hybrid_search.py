import math
import pytest
from engine.ai.embedding import EmbeddingEngine
from engine.db.session import get_db, init_db
from engine.db.repository import Repository

def test_embedding_engine_basics():
    engine = EmbeddingEngine()
    v1 = engine._local_hash_vector("深度学习 大语言模型 神经网络")
    v2 = engine._local_hash_vector("大语言模型 深度学习 变压器架构")
    v3 = engine._local_hash_vector("番茄炒蛋 美食制作 食谱做法")

    assert len(v1) == 256
    assert len(v2) == 256
    # L2 norm should be approximately 1.0
    norm1 = math.sqrt(sum(x * x for x in v1))
    assert abs(norm1 - 1.0) < 1e-3


    sim_same_domain = engine.cosine_similarity(v1, v2)
    sim_diff_domain = engine.cosine_similarity(v1, v3)

    # v1 and v2 should be much more similar than v1 and v3
    assert sim_same_domain > sim_diff_domain

def test_reciprocal_rank_fusion():
    engine = EmbeddingEngine()
    list_fts = ["doc1", "doc2", "doc3"]
    list_semantic = ["doc2", "doc4", "doc1"]

    rrf = engine.reciprocal_rank_fusion([list_fts, list_semantic], k=60)
    top_doc_id = rrf[0][0]
    # doc2 appears in both lists with high ranks (rank 2 in fts, rank 1 in semantic)
    assert top_doc_id == "doc2"
    assert len(rrf) == 4

def test_repository_hybrid_search(tmp_path):
    db_file = tmp_path / "test_search.db"
    init_db(db_file)
    with get_db(db_file) as conn:
        repo = Repository(conn)
        proj = repo.create_project("检索项目", "测试混合搜索")
        proj_id = proj["id"]
        target = repo.create_target(proj_id, "https://example.com")
        target_id = target["id"]
        job = repo.create_crawl_job(proj_id, "Job 1", {}, target_id=target_id)
        job_id = job["id"]

        # Doc 1: AI
        u1_obj = repo.create_url(project_id=proj_id, url="https://example.com/p1", normalized_url="https://example.com/p1", url_hash="h1_url", domain="example.com", job_id=job_id)
        u1 = u1_obj["id"]
        s1 = repo.create_snapshot(url_id=u1, job_id=job_id, project_id=proj_id, status_code=200, headers={}, raw_html_path="raw1.html", content_hash="h1")
        repo.create_document(
            snapshot_id=s1, project_id=proj_id, url_id=u1, doc_type="article",
            title="人工智能 AI 智能体 前沿进展", author="AI学者", published_at="2026-09-01",
            text="大模型 与 强化学习 在自主智能体 Agent 中的应用。", markdown="",
            language="zh", metadata={}, content_hash="h1"
        )

        # Doc 2: Cooking
        u2_obj = repo.create_url(project_id=proj_id, url="https://example.com/p2", normalized_url="https://example.com/p2", url_hash="h2_url", domain="example.com", job_id=job_id)
        u2 = u2_obj["id"]
        s2 = repo.create_snapshot(url_id=u2, job_id=job_id, project_id=proj_id, status_code=200, headers={}, raw_html_path="raw2.html", content_hash="h2")
        repo.create_document(
            snapshot_id=s2, project_id=proj_id, url_id=u2, doc_type="article",
            title="家常菜谱 美食 烹饪大全", author="大厨", published_at="2026-09-02",
            text="美味 红烧肉 与 清蒸鲈鱼 的家常烹饪技巧。", markdown="",
            language="zh", metadata={}, content_hash="h2"
        )

        # 1. FTS search
        fts_res, fts_total = repo.hybrid_search_documents(proj_id, "Agent", mode="fts")
        assert fts_total == 1
        assert "智能体" in fts_res[0]["title"]

        # 2. Semantic search
        sem_res, sem_total = repo.hybrid_search_documents(proj_id, "神经网络与深度学习算法", mode="semantic")
        assert sem_total == 2
        # First doc should be the AI one
        assert "智能体" in sem_res[0]["title"]

        # 3. Hybrid search
        hyb_res, hyb_total = repo.hybrid_search_documents(proj_id, "智能体", mode="hybrid")
        assert hyb_total >= 1
        assert "智能体" in hyb_res[0]["title"]
        assert "search_score" in hyb_res[0]


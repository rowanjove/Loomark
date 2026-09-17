import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from engine.db.session import init_db, get_db
from engine.db.repository import Repository
from engine.ai.research_agent import ResearchAgent, ResearchTask, ResearchAgentManager
from engine.fetcher.base import FetchResult

@pytest.fixture
def test_proj(tmp_path, monkeypatch):
    # Setup test db
    db_file = tmp_path / "test_research.db"
    init_db(db_file)
    monkeypatch.setattr("engine.ai.research_agent.get_db", lambda: get_db(db_file))
    with get_db(db_file) as conn:
        repo = Repository(conn)
        proj = repo.create_project("Autonomous AI Research", "Test project for research agent")
        proj_id = proj["id"]
    yield proj_id

@pytest.mark.asyncio
async def test_research_agent_full_loop(test_proj, monkeypatch):
    mock_ai = MagicMock()

    # 1. Mock decompose response
    async def mock_execute(task_type, content, title="", extra_params=None, **kwargs):
        if task_type == "research_decompose_v1":
            return {
                "task_type": task_type,
                "result": {
                    "text": json.dumps({
                        "sub_topics": ["机器人具身模型发展", "开源框架对比"],
                        "search_queries": ["具身智能 机器人开源框架 2026"]
                    })
                }
            }
        elif task_type == "relevance_scoring_v1":
            return {
                "task_type": task_type,
                "result": {
                    "text": json.dumps({
                        "score": 90,
                        "relevant": True,
                        "reason": "文章深入分析了具身智能核心框架与端到端控制"
                    })
                }
            }
        elif task_type == "knowledge_gap_v1":
            return {
                "task_type": task_type,
                "result": {
                    "text": json.dumps({
                        "is_sufficient": True, # Terminate early via sufficiency
                        "missing_aspects": []
                    })
                }
            }
        elif task_type == "project_report_v1":
            return {
                "task_type": task_type,
                "result": {
                    "text": "# 《具身智能开源框架》综合研究报告\n\n## 1. 行业趋势\n深度具身智能框架开源生态繁荣..."
                }
            }
        return {"result": {"text": "default"}}

    mock_ai.execute_task = AsyncMock(side_effect=mock_execute)

    agent = ResearchAgent(ai_client=mock_ai)

    # Mock fetcher
    sample_article_html = """
    <html><body>
        <h1>2026 具身智能开源机器人框架全面解析</h1>
        <p>本文探讨了当前主流的开源端到端具身智能与仿生机器人框架，重点包括控制器与感知端协同。详尽总结了性能与生态。</p>
        <a href="https://example.com/robot/docs/2">下一章节</a>
    </body></html>
    """
    mock_fetch_res = FetchResult(
        url="https://example.com/robot/frameworks",
        status_code=200,
        text=sample_article_html,
        response_time_ms=50
    )
    agent.fetcher.fetch = AsyncMock(return_value=mock_fetch_res)

    task = ResearchTask(
        task_id="res_test_1",
        project_id=test_proj,
        topic="具身智能机器人开源框架",
        max_pages=3,
        max_rounds=2
    )

    # Patch candidate discovery to return mock url
    with patch.object(agent, "_discover_initial_candidates", return_value=["https://example.com/robot/frameworks"]):
        await agent.execute(task)

    assert task.status == "COMPLETED"
    assert len(task.collected_doc_ids) >= 1
    assert task.final_report is not None
    assert "综合研究报告" in task.final_report
    assert any(s["stage"] == "PLANNING" for s in task.steps)
    assert any(s["stage"] == "COLLECTING" for s in task.steps)
    assert any(s["stage"] == "REPORTING" for s in task.steps)

def test_research_manager_lifecycle():
    mgr = ResearchAgentManager()
    task = mgr.start_task(
        project_id="dummy_proj",
        topic="量子计算与纠错码演进",
        max_pages=2,
        ai_client=None
    )
    assert task.task_id.startswith("research_")
    assert mgr.get_task(task.task_id) is not None

    stopped = mgr.stop_task(task.task_id)
    assert stopped is True
    assert task.status == "STOPPED"

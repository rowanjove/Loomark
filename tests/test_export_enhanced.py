import io
import os
import zipfile
import pytest
from pathlib import Path
from engine.db.session import get_db, init_db
from engine.db.repository import Repository
from engine.exporter.export_service import ExportService

@pytest.fixture
def repo_with_docs(tmp_path):
    db_file = tmp_path / "test_export.db"
    init_db(db_file)
    with get_db(db_file) as conn:
        repo = Repository(conn)
        proj = repo.create_project("导出测试项目", "用于测试多种新导出格式")
        proj_id = proj["id"]
        target = repo.create_target(proj_id, "https://example.com")
        target_id = target["id"]
        job = repo.create_crawl_job(proj_id, "Job 1", {}, target_id=target_id)
        job_id = job["id"]

        # Create 2 documents
        u1_obj = repo.create_url(project_id=proj_id, url="https://example.com/article1", normalized_url="https://example.com/article1", url_hash="hash_u1", domain="example.com", job_id=job_id)
        u1 = u1_obj["id"]
        s1 = repo.create_snapshot(url_id=u1, job_id=job_id, project_id=proj_id, status_code=200, headers={}, raw_html_path="raw1.html", content_hash="hash1")
        repo.create_document(
            snapshot_id=s1, project_id=proj_id, url_id=u1, doc_type="article",
            title="新能源汽车行业研究", author="张三", published_at="2026-09-01",
            text="新能源汽车发展迅速，锂电池与智能驾驶快速演进。", markdown="# 标题1\n\n正文内容1",
            language="zh", metadata={}, content_hash="hash1"
        )

        u2_obj = repo.create_url(project_id=proj_id, url="https://example.com/article2", normalized_url="https://example.com/article2", url_hash="hash_u2", domain="example.com", job_id=job_id)
        u2 = u2_obj["id"]
        s2 = repo.create_snapshot(url_id=u2, job_id=job_id, project_id=proj_id, status_code=200, headers={}, raw_html_path="raw2.html", content_hash="hash2")
        repo.create_document(
            snapshot_id=s2, project_id=proj_id, url_id=u2, doc_type="article",
            title="AI 智能体系统架构", author="李四", published_at="2026-09-02",
            text="Agent 架构包含规划、记忆与工具调用闭环。", markdown="# 标题2\n\n正文内容2",
            language="zh", metadata={}, content_hash="hash2"
        )


    return repo, proj_id, db_file


def test_export_xlsx(repo_with_docs):
    repo, proj_id, db_file = repo_with_docs
    with get_db(db_file) as conn:
        service = ExportService(Repository(conn))
        out_path = service.export_project(proj_id, format_type="xlsx")
        assert os.path.exists(out_path)
        assert out_path.endswith(".xlsx")

        # Verify it is a valid zip containing OpenXML worksheets
        with zipfile.ZipFile(out_path, "r") as zf:
            namelist = zf.namelist()
            assert "[Content_Types].xml" in namelist
            assert "xl/workbook.xml" in namelist
            assert "xl/worksheets/sheet1.xml" in namelist
            assert "xl/worksheets/sheet2.xml" in namelist

            # Sheet 2 should contain document title
            sheet2_content = zf.read("xl/worksheets/sheet2.xml").decode("utf-8")
            assert "新能源汽车行业研究" in sheet2_content
            assert "AI 智能体系统架构" in sheet2_content

def test_export_html_standalone(repo_with_docs):
    repo, proj_id, db_file = repo_with_docs
    with get_db(db_file) as conn:
        service = ExportService(Repository(conn))
        out_path = service.export_project(proj_id, format_type="html")
        assert os.path.exists(out_path)
        assert out_path.endswith(".html")

        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "<!DOCTYPE html>" in content
            assert "导出测试项目" in content
            assert "新能源汽车行业研究" in content
            assert "AI 智能体系统架构" in content
            assert "class=\"toc\"" in content

def test_export_txt(repo_with_docs):
    repo, proj_id, db_file = repo_with_docs
    with get_db(db_file) as conn:
        service = ExportService(Repository(conn))
        out_path = service.export_project(proj_id, format_type="txt")
        assert os.path.exists(out_path)
        assert out_path.endswith(".txt")

        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "项目: 导出测试项目" in content
            assert "文档总数: 2" in content
            assert "新能源汽车行业研究" in content
            assert "张三" in content

def test_export_parquet_requires_pyarrow(repo_with_docs):
    repo, proj_id, db_file = repo_with_docs
    with get_db(db_file) as conn:
        service = ExportService(Repository(conn))
        # If pyarrow is not installed, it should raise a descriptive RuntimeError
        try:
            import pyarrow
            out_path = service.export_project(proj_id, format_type="parquet")
            assert os.path.exists(out_path)
        except (ImportError, RuntimeError) as e:
            assert "pyarrow" in str(e)

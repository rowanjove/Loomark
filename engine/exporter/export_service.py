import csv
import io
import json
import xml.sax.saxutils as xml_escape
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from engine.db.repository import Repository
from engine.config import PROJECTS_DATA_DIR

class ExportService:
    """
    Exports captured and cleaned documents to Markdown (with YAML frontmatter),
    JSON, JSONL, CSV, Excel (.xlsx), Parquet (.parquet), standalone HTML, or TXT (PRD Section 78-80).
    """
    def __init__(self, repo: Repository):
        self.repo = repo

    def export_document_markdown(self, document: Dict[str, Any]) -> str:
        """Format a single document into Markdown with frontmatter."""
        meta = json.loads(document["metadata_json"]) if isinstance(document.get("metadata_json"), str) else (document.get("metadata_json") or {})
        frontmatter = [
            "---",
            f"title: \"{document.get('title', '').replace('\"', '\\\"')}\"",
            f"url: \"{document.get('url', '')}\"",
            f"domain: \"{document.get('domain', '')}\"",
            f"author: \"{document.get('author', '')}\"",
            f"published_at: \"{document.get('published_at', '')}\"",
            f"created_at: \"{document.get('created_at', '')}\"",
            f"type: \"{document.get('type', '')}\"",
            "---",
            "",
            f"# {document.get('title', 'Untitled')}",
            "",
            document.get("markdown") or document.get("text") or ""
        ]
        return "\n".join(frontmatter)

    def _generate_xlsx_bytes(self, project: Optional[Dict[str, Any]], docs: List[Dict[str, Any]]) -> bytes:
        """
        Pure-Python zero-dependency OpenXML (.xlsx) generator using zipfile.
        Produces multi-sheet workbook: Sheet 1 (Overview) and Sheet 2 (Documents).
        """
        def escape(val: Any) -> str:
            if val is None:
                return ""
            s = str(val)
            clean_s = "".join(c for c in s if ord(c) >= 32 or c in "\t\n\r")
            return xml_escape.escape(clean_s)

        def make_row(row_idx: int, cells: List[str]) -> str:
            cols = []
            for col_idx, cell_value in enumerate(cells):
                col_letter = ""
                temp = col_idx
                while True:
                    col_letter = chr(65 + (temp % 26)) + col_letter
                    temp = temp // 26 - 1
                    if temp < 0:
                        break
                cell_ref = f"{col_letter}{row_idx}"
                cols.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{escape(cell_value)}</t></is></c>')
            return f'<row r="{row_idx}">{"".join(cols)}</row>'

        # 1. Sheet 1: Overview
        sheet1_rows = [
            make_row(1, ["Loomark 采集项目数据导出报告", ""]),
            make_row(2, ["项目名称", project.get("name", "未命名项目") if project else ""]),
            make_row(3, ["项目 ID", project.get("id", "") if project else ""]),
            make_row(4, ["导出时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]),
            make_row(5, ["文档总数", str(len(docs))]),
            make_row(6, ["站点分布", f"{len(set(d.get('domain', '') for d in docs if d.get('domain')))} 个不同域名"]),
            make_row(7, ["", ""]),
            make_row(8, ["提示", "请切换至下方 '文档明细' 工作表查看全量明细数据。"])
        ]
        sheet1_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(sheet1_rows)}</sheetData>'
            '</worksheet>'
        )

        # 2. Sheet 2: Documents detail
        headers = ["序号", "ID", "标题", "URL", "域名", "作者", "发布时间", "类型", "字数", "正文缩略", "采集入库时间"]
        sheet2_rows = [make_row(1, headers)]
        for idx, doc in enumerate(docs):
            row_num = idx + 2
            text = doc.get("text") or ""
            preview_text = (text[:300] + "...") if len(text) > 300 else text
            sheet2_rows.append(make_row(row_num, [
                str(idx + 1),
                doc.get("id", ""),
                doc.get("title", ""),
                doc.get("url", ""),
                doc.get("domain", ""),
                doc.get("author", ""),
                doc.get("published_at", ""),
                doc.get("type", ""),
                str(len(text)),
                preview_text,
                doc.get("created_at", "")
            ]))
        sheet2_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(sheet2_rows)}</sheetData>'
            '</worksheet>'
        )

        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '</Types>'
        )

        rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        )

        wb_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>'
        )

        workbook = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets>'
            '<sheet name="概览" sheetId="1" r:id="rId1"/>'
            '<sheet name="文档明细" sheetId="2" r:id="rId2"/>'
            '</sheets>'
            '</workbook>'
        )

        styles = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="1"><font><name val="Calibri"/><sz val="11"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
            '</styleSheet>'
        )

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("_rels/.rels", rels)
            zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
            zf.writestr("xl/workbook.xml", workbook)
            zf.writestr("xl/styles.xml", styles)
            zf.writestr("xl/worksheets/sheet1.xml", sheet1_xml)
            zf.writestr("xl/worksheets/sheet2.xml", sheet2_xml)

        return buf.getvalue()

    def _generate_standalone_html(self, project: Optional[Dict[str, Any]], docs: List[Dict[str, Any]]) -> str:
        """Generate standalone responsive HTML ebook/archive report with TOC navigation."""
        proj_name = xml_escape.escape(project.get("name", "Loomark Export") if project else "Loomark Export")
        doc_nav_items = []
        doc_cards = []

        for idx, doc in enumerate(docs):
            title = xml_escape.escape(doc.get("title") or f"文档 #{idx+1}")
            url = xml_escape.escape(doc.get("url") or "")
            domain = xml_escape.escape(doc.get("domain") or "")
            author = xml_escape.escape(doc.get("author") or "未知作者")
            pub_date = xml_escape.escape(doc.get("published_at") or "")
            content = xml_escape.escape(doc.get("text") or "").replace("\n", "<br>")

            doc_nav_items.append(f'<li><a href="#doc-{idx+1}">{idx+1}. {title[:32]}</a></li>')
            doc_cards.append(f'''
            <article class="doc-card" id="doc-{idx+1}">
                <div class="doc-header">
                    <span class="doc-badge">#{idx+1}</span>
                    <h2 class="doc-title">{title}</h2>
                </div>
                <div class="doc-meta">
                    {f'<span class="meta-tag">🔗 <a href="{url}" target="_blank">{domain or "原文链接"}</a></span>' if url else ''}
                    <span class="meta-tag">👤 {author}</span>
                    {f'<span class="meta-tag">📅 {pub_date}</span>' if pub_date else ''}
                </div>
                <div class="doc-body">
                    {content}
                </div>
            </article>
            ''')

        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{proj_name} - 离线内容归档报告</title>
<style>
:root {{
    --bg-main: #09090b;
    --bg-card: #18181b;
    --border: #27272a;
    --text-main: #f4f4f5;
    --text-muted: #a1a1aa;
    --primary: #3b82f6;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg-main); color: var(--text-main); line-height: 1.6; display: flex; height: 100vh; overflow: hidden; }}
.sidebar {{ width: 320px; background: #121215; border-right: 1px solid var(--border); display: flex; flex-direction: column; }}
.sidebar-header {{ padding: 20px; border-bottom: 1px solid var(--border); }}
.sidebar-header h1 {{ font-size: 16px; font-weight: 600; color: #fff; }}
.sidebar-header p {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; }}
.toc {{ list-style: none; overflow-y: auto; flex: 1; padding: 12px; }}
.toc li a {{ display: block; padding: 8px 12px; border-radius: 6px; color: var(--text-muted); text-decoration: none; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.toc li a:hover {{ background: #27272a; color: #fff; }}
.main-content {{ flex: 1; overflow-y: auto; padding: 40px; }}
.container {{ max-width: 880px; margin: 0 auto; }}
.doc-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 28px; margin-bottom: 32px; }}
.doc-header {{ display: flex; align-items: flex-start; gap: 12px; margin-bottom: 12px; }}
.doc-badge {{ background: #27272a; color: var(--text-muted); padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; font-mono: true; }}
.doc-title {{ font-size: 20px; font-weight: 600; color: #fff; }}
.doc-meta {{ display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 20px; padding-bottom: 14px; border-bottom: 1px solid var(--border); font-size: 12px; color: var(--text-muted); }}
.meta-tag a {{ color: var(--primary); text-decoration: none; }}
.meta-tag a:hover {{ text-decoration: underline; }}
.doc-body {{ font-size: 14px; color: #d4d4d8; line-height: 1.8; word-break: break-word; }}
</style>
</head>
<body>
<div class="sidebar">
    <div class="sidebar-header">
        <h1>{proj_name}</h1>
        <p>共归档 {len(docs)} 篇文档 · 导出于 {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
    </div>
    <ul class="toc">
        {''.join(doc_nav_items)}
    </ul>
</div>
<div class="main-content">
    <div class="container">
        {''.join(doc_cards)}
    </div>
</div>
</body>
</html>'''
        return html

    def export_project(self, project_id: str, format_type: str = "markdown",
                       doc_ids: Optional[List[str]] = None) -> str:
        """Export documents and return path to the generated archive/file."""
        export_dir = PROJECTS_DATA_DIR / project_id / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        project = self.repo.get_project(project_id)

        # Retrieve documents
        if doc_ids:
            docs = [self.repo.get_document(did) for did in doc_ids]
            docs = [d for d in docs if d is not None]
        else:
            docs, _ = self.repo.list_documents(project_id, limit=5000)

        format_type = format_type.lower().strip()

        if format_type == "markdown":
            batch_dir = export_dir / f"export_md_{len(docs)}"
            batch_dir.mkdir(parents=True, exist_ok=True)
            for idx, doc in enumerate(docs):
                clean_title = "".join(c for c in doc.get("title", f"doc_{idx}") if c.isalnum() or c in " _-")[:50].strip()
                filename = f"{idx+1:03d}_{clean_title or 'doc'}.md"
                content = self.export_document_markdown(doc)
                with open(batch_dir / filename, "w", encoding="utf-8") as f:
                    f.write(content)
            return str(batch_dir)

        elif format_type == "json":
            out_file = export_dir / f"export_{len(docs)}.json"
            clean_docs = []
            for d in docs:
                item = dict(d)
                if isinstance(item.get("metadata_json"), str):
                    try:
                        item["metadata"] = json.loads(item["metadata_json"])
                    except Exception:
                        item["metadata"] = {}
                clean_docs.append(item)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(clean_docs, f, ensure_ascii=False, indent=2)
            return str(out_file)

        elif format_type == "jsonl":
            out_file = export_dir / f"export_{len(docs)}.jsonl"
            with open(out_file, "w", encoding="utf-8") as f:
                for d in docs:
                    f.write(json.dumps(dict(d), ensure_ascii=False) + "\n")
            return str(out_file)

        elif format_type == "csv":
            out_file = export_dir / f"export_{len(docs)}.csv"
            fields = ["id", "title", "url", "domain", "author", "published_at", "type", "created_at", "text"]

            def sanitize_csv_val(val: Any) -> str:
                if val is None:
                    return ""
                s = str(val)
                if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
                    return f"'{s}"
                return s

            with open(out_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                for d in docs:
                    row = {}
                    for k in fields:
                        v = d.get(k, "")
                        if k == "text":
                            v = (v or "")[:2000]
                        row[k] = sanitize_csv_val(v)
                    writer.writerow(row)
            return str(out_file)

        elif format_type in ("xlsx", "excel"):
            out_file = export_dir / f"export_{len(docs)}.xlsx"
            xlsx_bytes = self._generate_xlsx_bytes(project, docs)
            with open(out_file, "wb") as f:
                f.write(xlsx_bytes)
            return str(out_file)

        elif format_type == "html":
            out_file = export_dir / f"export_{len(docs)}.html"
            html_content = self._generate_standalone_html(project, docs)
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            return str(out_file)

        elif format_type == "txt":
            out_file = export_dir / f"export_{len(docs)}.txt"
            lines = []
            proj_title = project.get("name", "Loomark Content Export") if project else "Loomark Content Export"
            lines.append("=" * 80)
            lines.append(f"项目: {proj_title}")
            lines.append(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"文档总数: {len(docs)}")
            lines.append("=" * 80 + "\n")

            for idx, doc in enumerate(docs):
                lines.append("-" * 60)
                lines.append(f"[{idx+1}] {doc.get('title', '未命名文档')}")
                if doc.get("url"):
                    lines.append(f"来源 URL: {doc.get('url')}")
                if doc.get("author"):
                    lines.append(f"作者: {doc.get('author')}")
                if doc.get("published_at"):
                    lines.append(f"发布时间: {doc.get('published_at')}")
                lines.append("-" * 60)
                lines.append((doc.get("text") or "").strip())
                lines.append("\n\n")

            with open(out_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return str(out_file)

        elif format_type == "parquet":
            try:
                import pyarrow as pa
                import pyarrow.parquet as pq
            except ImportError:
                raise RuntimeError(
                    "导出 Parquet 列式数据需要 pyarrow 库。"
                    "请在命令行运行: pip install pyarrow 即可启用该功能。"
                )

            out_file = export_dir / f"export_{len(docs)}.parquet"
            data = {
                "id": [str(d.get("id", "")) for d in docs],
                "title": [str(d.get("title", "")) for d in docs],
                "url": [str(d.get("url", "")) for d in docs],
                "domain": [str(d.get("domain", "")) for d in docs],
                "author": [str(d.get("author", "")) for d in docs],
                "published_at": [str(d.get("published_at", "")) for d in docs],
                "type": [str(d.get("type", "")) for d in docs],
                "text": [str(d.get("text", "")) for d in docs],
                "created_at": [str(d.get("created_at", "")) for d in docs],
            }
            table = pa.Table.from_pydict(data)
            pq.write_table(table, str(out_file))
            return str(out_file)

        else:
            raise ValueError(f"Unsupported format: {format_type}. Supported: markdown, json, jsonl, csv, xlsx, html, txt, parquet")


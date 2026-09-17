import uuid
import json
import sqlite3
from typing import List, Optional, Dict, Any, Tuple
from engine.db.session import get_db

class Repository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # --- Project Methods ---
    def create_project(self, name: str, description: str = "") -> Dict[str, Any]:
        proj_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO projects (id, name, description) VALUES (?, ?, ?);",
            (proj_id, name, description)
        )
        return self.get_project(proj_id)

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            """
            SELECT p.*,
                   (SELECT COUNT(*) FROM targets WHERE project_id = p.id) AS target_count,
                   (SELECT COUNT(*) FROM documents WHERE project_id = p.id) AS document_count
            FROM projects p
            WHERE p.id = ?;
            """,
            (project_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_projects(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT p.*,
                   (SELECT COUNT(*) FROM targets WHERE project_id = p.id) AS target_count,
                   (SELECT COUNT(*) FROM documents WHERE project_id = p.id) AS document_count
            FROM projects p
            ORDER BY p.updated_at DESC;
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_project(self, project_id: str) -> bool:
        cur = self.conn.execute("DELETE FROM projects WHERE id = ?;", (project_id,))
        return cur.rowcount > 0

    # --- Target Methods ---
    def create_target(self, project_id: str, url: str, scope: str = "domain",
                      scope_regex: Optional[str] = None, adapter_id: str = "auto") -> Dict[str, Any]:
        target_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO targets (id, project_id, url, scope, scope_regex, adapter_id)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (target_id, project_id, url, scope, scope_regex, adapter_id)
        )
        row = self.conn.execute("SELECT * FROM targets WHERE id = ?;", (target_id,)).fetchone()
        return dict(row)

    def list_targets(self, project_id: str) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM targets WHERE project_id = ? ORDER BY created_at DESC;",
            (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Crawl Job Methods ---
    def create_crawl_job(self, project_id: str, name: str, config: Dict[str, Any],
                         target_id: Optional[str] = None) -> Dict[str, Any]:
        job_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO crawl_jobs (id, project_id, target_id, name, status, config_json, stats_json)
            VALUES (?, ?, ?, ?, 'PENDING', ?, ?);
            """,
            (job_id, project_id, target_id, name, json.dumps(config), json.dumps({}))
        )
        return self.get_crawl_job(job_id)

    def get_crawl_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute("SELECT * FROM crawl_jobs WHERE id = ?;", (job_id,)).fetchone()
        return dict(row) if row else None

    def list_crawl_jobs(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if project_id:
            rows = self.conn.execute(
                "SELECT * FROM crawl_jobs WHERE project_id = ? ORDER BY created_at DESC;",
                (project_id,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM crawl_jobs ORDER BY created_at DESC;"
            ).fetchall()
        return [dict(r) for r in rows]

    def update_job_status(self, job_id: str, status: str, started: bool = False, finished: bool = False):
        if started:
            self.conn.execute(
                "UPDATE crawl_jobs SET status = ?, started_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (status, job_id)
            )
        elif finished:
            self.conn.execute(
                "UPDATE crawl_jobs SET status = ?, finished_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (status, job_id)
            )
        else:
            self.conn.execute("UPDATE crawl_jobs SET status = ? WHERE id = ?;", (status, job_id))

    def update_job_stats(self, job_id: str, stats: Dict[str, Any]):
        self.conn.execute(
            "UPDATE crawl_jobs SET stats_json = ? WHERE id = ?;",
            (json.dumps(stats), job_id)
        )

    # --- URL Frontier Methods ---
    def insert_urls_batch(self, urls_data: List[Dict[str, Any]]) -> int:
        """Batch insert discovered URLs, ignoring already queued/processed identical hashes within the job."""
        if not urls_data:
            return 0
        inserted = 0
        for item in urls_data:
            try:
                cur = self.conn.execute(
                    """
                    INSERT OR IGNORE INTO urls (id, job_id, project_id, url, normalized_url, url_hash,
                                                domain, depth, priority, status, parent_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        item.get("id") or str(uuid.uuid4()),
                        item["job_id"],
                        item["project_id"],
                        item["url"],
                        item["normalized_url"],
                        item["url_hash"],
                        item["domain"],
                        item.get("depth", 0),
                        item.get("priority", 0),
                        item.get("status", "QUEUED"),
                        item.get("parent_url")
                    )
                )
                if cur.rowcount > 0:
                    inserted += 1
            except sqlite3.IntegrityError:
                continue
        return inserted

    def create_url(self, project_id: str, url: str, normalized_url: str, url_hash: str,
                   domain: str, status: str = "FETCHED", job_id: Optional[str] = None) -> Dict[str, Any]:
        url_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO urls (id, job_id, project_id, url, normalized_url, url_hash, domain, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (url_id, job_id, project_id, url, normalized_url, url_hash, domain, status)
        )
        return {"id": url_id, "url": url, "normalized_url": normalized_url, "url_hash": url_hash, "domain": domain}

    def check_url_exists_in_job(self, job_id: str, url_hash: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM urls WHERE job_id = ? AND url_hash = ? LIMIT 1;",
            (job_id, url_hash)
        ).fetchone()
        return bool(row)

    def get_latest_content_hash(self, project_id: str, url_hash: str) -> Optional[str]:
        """Find the latest content_hash for incremental detection across previous snapshots."""
        row = self.conn.execute(
            """
            SELECT s.content_hash
            FROM snapshots s
            JOIN urls u ON s.url_id = u.id
            WHERE u.project_id = ? AND u.url_hash = ?
            ORDER BY s.fetched_at DESC LIMIT 1;
            """,
            (project_id, url_hash)
        ).fetchone()
        return row["content_hash"] if row else None

    def get_latest_document_by_url_hash(self, project_id: str, url_hash: str) -> Optional[Dict[str, Any]]:
        """Find the latest document for incremental comparison across previous snapshots."""
        row = self.conn.execute(
            """
            SELECT d.*
            FROM documents d
            JOIN urls u ON d.url_id = u.id
            WHERE u.project_id = ? AND u.url_hash = ?
            ORDER BY d.created_at DESC LIMIT 1;
            """,
            (project_id, url_hash)
        ).fetchone()
        return dict(row) if row else None

    def pop_next_urls_for_domains(self, job_id: str, eligible_domains: List[str],
                                  limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch candidate URLs for given domains ordered by priority."""
        if not eligible_domains:
            # Fallback to any domain
            rows = self.conn.execute(
                """
                SELECT * FROM urls
                WHERE job_id = ? AND status = 'QUEUED'
                ORDER BY priority DESC, depth ASC, id ASC
                LIMIT ?;
                """,
                (job_id, limit)
            ).fetchall()
        else:
            placeholders = ",".join("?" for _ in eligible_domains)
            rows = self.conn.execute(
                f"""
                SELECT * FROM urls
                WHERE job_id = ? AND status = 'QUEUED' AND domain IN ({placeholders})
                ORDER BY priority DESC, depth ASC, id ASC
                LIMIT ?;
                """,
                [job_id] + eligible_domains + [limit]
            ).fetchall()
        return [dict(r) for r in rows]

    def update_url_status(self, url_id: str, status: str, error_message: Optional[str] = None):
        self.conn.execute(
            """
            UPDATE urls
            SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
            """,
            (status, error_message, url_id)
        )

    def increment_url_retry(self, url_id: str, error_message: str):
        self.conn.execute(
            """
            UPDATE urls
            SET status = 'QUEUED', retry_count = retry_count + 1, error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
            """,
            (error_message, url_id)
        )

    def get_job_url_counts(self, job_id: str) -> Dict[str, int]:
        rows = self.conn.execute(
            "SELECT status, COUNT(*) as cnt FROM urls WHERE job_id = ? GROUP BY status;",
            (job_id,)
        ).fetchall()
        counts = {"DISCOVERED": 0, "QUEUED": 0, "FETCHING": 0, "FETCHED": 0, "PARSED": 0, "FAILED": 0, "SKIPPED": 0}
        for r in rows:
            counts[r["status"]] = r["cnt"]
        counts["total"] = sum(counts.values())
        return counts

    def retry_all_failed_urls(self, job_id: str) -> int:
        cur = self.conn.execute(
            "UPDATE urls SET status = 'QUEUED', error_message = NULL WHERE job_id = ? AND status = 'FAILED';",
            (job_id,)
        )
        return cur.rowcount

    # --- Snapshot & Document Methods ---
    def create_snapshot(self, url_id: str, job_id: str, project_id: str, status_code: int,
                        headers: Dict[str, Any], raw_html_path: Optional[str],
                        content_hash: str, response_time_ms: int = 0) -> str:
        snap_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO snapshots (id, url_id, job_id, project_id, status_code, headers_json,
                                  raw_html_path, content_hash, response_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (snap_id, url_id, job_id, project_id, status_code, json.dumps(headers),
             raw_html_path, content_hash, response_time_ms)
        )
        return snap_id

    def create_document(self, snapshot_id: str, project_id: str, url_id: str,
                        doc_type: str, title: str, author: str, published_at: Optional[str],
                        text: str, markdown: str, language: str, metadata: Dict[str, Any],
                        content_hash: str, change_status: str = "NEW",
                        diff_summary: Optional[str] = None) -> str:
        doc_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO documents (id, snapshot_id, project_id, url_id, type, title, author,
                                   published_at, text, markdown, language, metadata_json,
                                   content_hash, change_status, diff_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (doc_id, snapshot_id, project_id, url_id, doc_type, title, author,
             published_at, text, markdown, language, json.dumps(metadata, default=str),
             content_hash, change_status, diff_summary)
        )
        return doc_id

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            """
            SELECT d.*, u.url, u.domain, s.raw_html_path, s.status_code, s.fetched_at
            FROM documents d
            JOIN urls u ON d.url_id = u.id
            JOIN snapshots s ON d.snapshot_id = s.id
            WHERE d.id = ?;
            """,
            (doc_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_documents(self, project_id: str, search: Optional[str] = None,
                       domain: Optional[str] = None, doc_type: Optional[str] = None,
                       limit: int = 50, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """Search and filter documents using FTS5 when search query is provided."""
        params: List[Any] = [project_id]
        where_clauses = ["d.project_id = ?"]

        if search:
            # Clean and sanitize search query for FTS5
            import re
            cleaned = re.sub(r'["\'*^:()\-+]', ' ', search).strip()
            tokens = [t for t in cleaned.split() if t]
            if tokens:
                fts_query = " ".join(f'"{t}"*' for t in tokens)
            else:
                fts_query = f'"{search.replace("\"", "")}"*'

            try:
                sql = f"""
                    SELECT d.*, u.url, u.domain
                    FROM documents_fts fts
                    JOIN documents d ON fts.document_id = d.id
                    JOIN urls u ON d.url_id = u.id
                    WHERE fts.documents_fts MATCH ? AND d.project_id = ?
                """
                params = [fts_query, project_id]
                if domain:
                    sql += " AND u.domain = ?"
                    params.append(domain)
                if doc_type:
                    sql += " AND d.type = ?"
                    params.append(doc_type)

                count_sql = f"SELECT COUNT(*) FROM ({sql})"
                total = self.conn.execute(count_sql, params).fetchone()[0]

                sql += " ORDER BY rank LIMIT ? OFFSET ?;"
                rows = self.conn.execute(sql, params + [limit, offset]).fetchall()
                return [dict(r) for r in rows], total
            except sqlite3.OperationalError:
                # Graceful fallback to LIKE query if FTS5 syntax fails
                where_clauses = ["d.project_id = ?", "(d.title LIKE ? OR d.text LIKE ?)"]
                params = [project_id, f"%{search}%", f"%{search}%"]
                if domain:
                    where_clauses.append("u.domain = ?")
                    params.append(domain)
                if doc_type:
                    where_clauses.append("d.type = ?")
                    params.append(doc_type)

                where_str = " AND ".join(where_clauses)
                count_sql = f"""
                    SELECT COUNT(*)
                    FROM documents d
                    JOIN urls u ON d.url_id = u.id
                    WHERE {where_str};
                """
                total = self.conn.execute(count_sql, params).fetchone()[0]
                sql = f"""
                    SELECT d.*, u.url, u.domain
                    FROM documents d
                    JOIN urls u ON d.url_id = u.id
                    WHERE {where_str}
                    ORDER BY d.created_at DESC
                    LIMIT ? OFFSET ?;
                """
                rows = self.conn.execute(sql, params + [limit, offset]).fetchall()
                return [dict(r) for r in rows], total

        else:
            if domain:
                where_clauses.append("u.domain = ?")
                params.append(domain)
            if doc_type:
                where_clauses.append("d.type = ?")
                params.append(doc_type)

            where_str = " AND ".join(where_clauses)
            count_sql = f"""
                SELECT COUNT(*)
                FROM documents d
                JOIN urls u ON d.url_id = u.id
                WHERE {where_str};
            """
            total = self.conn.execute(count_sql, params).fetchone()[0]

            sql = f"""
                SELECT d.*, u.url, u.domain
                FROM documents d
                JOIN urls u ON d.url_id = u.id
                WHERE {where_str}
                ORDER BY d.created_at DESC
                LIMIT ? OFFSET ?;
            """
            params.extend([limit, offset])
            rows = self.conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows], total

    def get_document_snapshots_history(self, document_id: str) -> List[Dict[str, Any]]:
        """Get history snapshots for the URL associated with this document."""
        row = self.conn.execute("SELECT url_id FROM documents WHERE id = ?;", (document_id,)).fetchone()
        if not row:
            return []
        url_id = row["url_id"]
        rows = self.conn.execute(
            """
            SELECT s.*, d.id as doc_id, d.title, d.change_status, d.diff_summary
            FROM snapshots s
            LEFT JOIN documents d ON d.snapshot_id = s.id
            WHERE s.url_id = ?
            ORDER BY s.fetched_at DESC;
            """,
            (url_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Subtitles ---
    def create_subtitle(self, document_id: str, language: str, source: str,
                        segments: List[Dict[str, Any]]) -> str:
        sub_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO subtitles (id, document_id, language, source, segments_json)
            VALUES (?, ?, ?, ?, ?);
            """,
            (sub_id, document_id, language, source, json.dumps(segments))
        )
        return sub_id

    def get_subtitles_for_document(self, document_id: str) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM subtitles WHERE document_id = ?;", (document_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- AI Artifacts & Cache ---
    def create_ai_artifact(self, document_id: str, project_id: str, artifact_type: str,
                           model: str, provider: str, prompt_version: str, result_json: Dict[str, Any],
                           input_tokens: int = 0, output_tokens: int = 0, cost: float = 0.0) -> str:
        art_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO ai_artifacts (id, document_id, project_id, type, model, provider,
                                      prompt_version, result_json, input_tokens, output_tokens, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (art_id, document_id, project_id, artifact_type, model, provider, prompt_version,
             json.dumps(result_json), input_tokens, output_tokens, cost)
        )
        return art_id

    def get_ai_artifacts_for_document(self, document_id: str) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM ai_artifacts WHERE document_id = ? ORDER BY created_at DESC;",
            (document_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_ai_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM ai_cache WHERE cache_key = ?;", (cache_key,)
        ).fetchone()
        return dict(row) if row else None

    def set_ai_cache(self, cache_key: str, result_json: Dict[str, Any],
                     input_tokens: int = 0, output_tokens: int = 0):
        self.conn.execute(
            """
            INSERT OR REPLACE INTO ai_cache (cache_key, result_json, input_tokens, output_tokens)
            VALUES (?, ?, ?, ?);
            """,
            (cache_key, json.dumps(result_json), input_tokens, output_tokens)
        )

    def get_project_ai_cost(self, project_id: str) -> Dict[str, Any]:
        row = self.conn.execute(
            """
            SELECT COUNT(*) as artifact_count,
                   SUM(input_tokens) as total_input_tokens,
                   SUM(output_tokens) as total_output_tokens,
                   SUM(cost) as total_cost
            FROM ai_artifacts
            WHERE project_id = ?;
            """,
            (project_id,)
        ).fetchone()
        return {
            "artifact_count": row["artifact_count"] or 0,
            "total_input_tokens": row["total_input_tokens"] or 0,
            "total_output_tokens": row["total_output_tokens"] or 0,
            "total_cost": round(row["total_cost"] or 0.0, 4)
        }

    # --- Logs ---
    def add_crawl_log(self, job_id: str, level: str, message: str):
        self.conn.execute(
            "INSERT INTO crawl_logs (job_id, level, message) VALUES (?, ?, ?);",
            (job_id, level, message)
        )

    def get_job_logs(self, job_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM crawl_logs WHERE job_id = ? ORDER BY id DESC LIMIT ?;",
            (job_id, limit)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    # --- Monitoring Schedules & Events (PRD Section 75-77, 104) ---
    def create_monitor_schedule(self, project_id: str, name: str, url: str,
                                interval_minutes: int = 60, target_id: Optional[str] = None,
                                schedule_type: str = "interval", cron_expression: Optional[str] = None) -> Dict[str, Any]:
        schedule_id = str(uuid.uuid4())
        from engine.scheduler.cron_parser import CronParser
        next_run_dt_str = None
        if schedule_type == "cron" and cron_expression:
            try:
                next_dt = CronParser.get_next_run(cron_expression)
                next_run_dt_str = next_dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

        if next_run_dt_str:
            self.conn.execute(
                """
                INSERT INTO monitor_schedules (id, project_id, target_id, name, url, interval_minutes, schedule_type, cron_expression, enabled, next_run_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?);
                """,
                (schedule_id, project_id, target_id, name, url, interval_minutes, schedule_type, cron_expression, next_run_dt_str)
            )
        else:
            self.conn.execute(
                """
                INSERT INTO monitor_schedules (id, project_id, target_id, name, url, interval_minutes, schedule_type, cron_expression, enabled, next_run_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP);
                """,
                (schedule_id, project_id, target_id, name, url, interval_minutes, schedule_type, cron_expression)
            )
        row = self.conn.execute("SELECT * FROM monitor_schedules WHERE id = ?;", (schedule_id,)).fetchone()
        return dict(row)

    def list_monitor_schedules(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if project_id:
            rows = self.conn.execute(
                "SELECT * FROM monitor_schedules WHERE project_id = ? ORDER BY created_at DESC;",
                (project_id,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM monitor_schedules ORDER BY created_at DESC;"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_due_monitor_schedules(self) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT * FROM monitor_schedules
            WHERE enabled = 1 AND (next_run_at IS NULL OR next_run_at <= CURRENT_TIMESTAMP);
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def update_monitor_schedule_run(self, schedule_id: str, interval_minutes: int = 60,
                                   schedule_type: str = "interval", cron_expression: Optional[str] = None):
        if schedule_type == "cron" and cron_expression:
            try:
                from engine.scheduler.cron_parser import CronParser
                next_dt = CronParser.get_next_run(cron_expression)
                next_str = next_dt.strftime("%Y-%m-%d %H:%M:%S")
                self.conn.execute(
                    """
                    UPDATE monitor_schedules
                    SET last_run_at = CURRENT_TIMESTAMP,
                        next_run_at = ?
                    WHERE id = ?;
                    """,
                    (next_str, schedule_id)
                )
                return
            except Exception:
                pass

        self.conn.execute(
            """
            UPDATE monitor_schedules
            SET last_run_at = CURRENT_TIMESTAMP,
                next_run_at = datetime('now', '+' || ? || ' minutes')
            WHERE id = ?;
            """,
            (interval_minutes, schedule_id)
        )

    def toggle_monitor_schedule(self, schedule_id: str, enabled: bool):
        self.conn.execute(
            "UPDATE monitor_schedules SET enabled = ? WHERE id = ?;",
            (1 if enabled else 0, schedule_id)
        )

    def delete_monitor_schedule(self, schedule_id: str) -> bool:
        cur = self.conn.execute("DELETE FROM monitor_schedules WHERE id = ?;", (schedule_id,))
        return cur.rowcount > 0

    def create_monitor_event(self, project_id: str, schedule_id: Optional[str],
                             url: str, event_type: str, old_content_hash: Optional[str] = None,
                             new_content_hash: Optional[str] = None,
                             ai_change_summary: Optional[str] = None) -> str:
        event_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO monitor_events (id, project_id, schedule_id, url, event_type,
                                       old_content_hash, new_content_hash, ai_change_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (event_id, project_id, schedule_id, url, event_type,
             old_content_hash, new_content_hash, ai_change_summary)
        )
        return event_id

    def list_monitor_events(self, project_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        if project_id:
            rows = self.conn.execute(
                """
                SELECT e.*, s.name as schedule_name
                FROM monitor_events e
                LEFT JOIN monitor_schedules s ON e.schedule_id = s.id
                WHERE e.project_id = ?
                ORDER BY e.created_at DESC LIMIT ?;
                """,
                (project_id, limit)
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT e.*, s.name as schedule_name
                FROM monitor_events e
                LEFT JOIN monitor_schedules s ON e.schedule_id = s.id
                ORDER BY e.created_at DESC LIMIT ?;
                """,
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # --- Document Chunks (PRD Section 45, 52) ---
    def create_chunk(self, document_id: str, project_id: str, chunk_index: int,
                     text: str, char_count: int, token_count: int,
                     summary: Optional[str] = None) -> str:
        chunk_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO chunks (id, document_id, project_id, chunk_index, text, char_count, token_count, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (chunk_id, document_id, project_id, chunk_index, text, char_count, token_count, summary)
        )
        return chunk_id

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT * FROM chunks
            WHERE document_id = ?
            ORDER BY chunk_index ASC;
            """,
            (document_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Document Embeddings & Hybrid Search (PRD Section 42, 61, 74) ---
    def save_document_embedding(self, document_id: str, project_id: str, model: str, vector: List[float]) -> str:
        emb_id = str(uuid.uuid4())
        self.conn.execute(
            """
            INSERT INTO document_embeddings (id, document_id, project_id, model, vector_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(document_id, model) DO UPDATE SET
                vector_json = excluded.vector_json;
            """,
            (emb_id, document_id, project_id, model, json.dumps(vector))
        )
        return emb_id

    def get_document_embedding(self, document_id: str, model: str = "default") -> Optional[List[float]]:
        row = self.conn.execute(
            "SELECT vector_json FROM document_embeddings WHERE document_id = ? AND model = ?;",
            (document_id, model)
        ).fetchone()
        if not row:
            return None
        return json.loads(row["vector_json"])

    def hybrid_search_documents(
        self,
        project_id: str,
        query: str,
        mode: str = "hybrid",
        domain: Optional[str] = None,
        doc_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Hybrid retrieval combining FTS5 BM25 with dense vector cosine similarity
        using Reciprocal Rank Fusion (RRF).
        """
        from engine.ai.embedding import embedding_engine

        if not query or not query.strip():
            return self.list_documents(project_id, domain=domain, doc_type=doc_type, limit=limit, offset=offset)

        clean_query = query.strip()
        mode = mode.lower().strip()

        if mode == "fts":
            return self.list_documents(project_id, search=clean_query, domain=domain, doc_type=doc_type, limit=limit, offset=offset)

        # 1. Fetch all candidate documents in this project matching filters
        where_clauses = ["d.project_id = ?"]
        params = [project_id]
        if domain:
            where_clauses.append("u.domain = ?")
            params.append(domain)
        if doc_type:
            where_clauses.append("d.type = ?")
            params.append(doc_type)

        cand_sql = f"""
            SELECT d.id, d.title, substr(d.text, 1, 400) as text, substr(d.markdown, 1, 400) as markdown,
                   d.type, d.author, d.published_at, d.created_at,
                   u.url, u.domain, de.vector_json
            FROM documents d
            JOIN urls u ON d.url_id = u.id
            LEFT JOIN document_embeddings de ON de.document_id = d.id AND de.model = 'default'
            WHERE {' AND '.join(where_clauses)}
            ORDER BY d.created_at DESC
            LIMIT 500;
        """
        cand_rows = self.conn.execute(cand_sql, params).fetchall()
        if not cand_rows:
            return [], 0

        # 2. Compute query vector
        query_vec = embedding_engine.get_embedding_sync(clean_query)

        # 3. Compute semantic similarity
        scored_docs = []
        for r in cand_rows:
            doc_id = r["id"]
            if r["vector_json"]:
                doc_vec = json.loads(r["vector_json"])
            else:
                # Lazy embedding calculation and persistence
                content_sample = f"{r['title'] or ''} {(r['text'] or '')[:1000]}"
                doc_vec = embedding_engine.get_embedding_sync(content_sample)
                self.save_document_embedding(doc_id, project_id, "default", doc_vec)

            # Dimension safety guard: fall back to local vector if model dimensions mismatch
            if len(query_vec) != len(doc_vec):
                doc_vec = embedding_engine.get_embedding_sync(f"{r['title'] or ''} {(r['text'] or '')[:1000]}")

            sim = embedding_engine.cosine_similarity(query_vec, doc_vec)
            scored_docs.append((doc_id, sim, dict(r)))

        # Sort by semantic similarity descending
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        semantic_rank_ids = [item[0] for item in scored_docs]
        doc_map = {item[0]: item[2] for item in scored_docs}

        if mode == "semantic":
            total = len(scored_docs)
            slice_ids = semantic_rank_ids[offset:offset + limit]
            results = []
            for did in slice_ids:
                d = doc_map[did]
                d.pop("vector_json", None)
                results.append(d)
            return results, total

        # 4. Mode == "hybrid": Perform FTS5 search and merge via RRF
        fts_docs, _ = self.list_documents(
            project_id=project_id,
            search=clean_query,
            domain=domain,
            doc_type=doc_type,
            limit=200,
            offset=0
        )
        fts_rank_ids = [d["id"] for d in fts_docs]
        for d in fts_docs:
            did = d["id"]
            if did not in doc_map:
                doc_map[did] = d

        # Combine via RRF
        rrf_ranked = embedding_engine.reciprocal_rank_fusion([fts_rank_ids, semantic_rank_ids], k=60)
        total = len(rrf_ranked)
        slice_items = rrf_ranked[offset:offset + limit]

        results = []
        for did, rrf_score in slice_items:
            d = doc_map.get(did)
            if not d:
                d = self.get_document(did)
            if d:
                clean_d = dict(d)
                clean_d.pop("vector_json", None)
                clean_d["search_score"] = round(rrf_score, 4)
                results.append(clean_d)

        return results, total

    # --- Research Task Persistence ---
    def create_research_task(self, task_id: str, project_id: str, topic: str,
                             max_pages: int = 5, max_rounds: int = 3, min_relevance: int = 60) -> Dict[str, Any]:
        self.conn.execute(
            """
            INSERT INTO research_tasks (id, project_id, topic, status, max_pages, max_rounds, min_relevance,
                                       sub_topics_json, search_queries_json, collected_doc_ids_json, steps_json)
            VALUES (?, ?, ?, 'INITIALIZING', ?, ?, ?, '[]', '[]', '[]', '[]');
            """,
            (task_id, project_id, topic, max_pages, max_rounds, min_relevance)
        )
        return self.get_research_task(task_id)

    def update_research_task(self, task_id: str, **kwargs):
        set_clauses = []
        values = []
        for k, v in kwargs.items():
            if v is not None:
                if k in ("sub_topics", "search_queries", "collected_doc_ids", "steps"):
                    col_name = f"{k}_json"
                    set_clauses.append(f"{col_name} = ?")
                    values.append(json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v))
                else:
                    set_clauses.append(f"{k} = ?")
                    values.append(v)

        if "finished_at" not in kwargs and kwargs.get("status") in ("COMPLETED", "FAILED", "STOPPED"):
            set_clauses.append("finished_at = CURRENT_TIMESTAMP")

        if not set_clauses:
            return

        values.append(task_id)
        sql = f"UPDATE research_tasks SET {', '.join(set_clauses)} WHERE id = ?;"
        self.conn.execute(sql, values)

    def get_research_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute("SELECT * FROM research_tasks WHERE id = ?;", (task_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        for json_key in ("sub_topics", "search_queries", "collected_doc_ids", "steps"):
            raw = d.get(f"{json_key}_json")
            try:
                d[json_key] = json.loads(raw) if raw else []
            except Exception:
                d[json_key] = []
        d["task_id"] = d["id"]
        d["collected_count"] = len(d["collected_doc_ids"])
        return d

    def list_research_tasks(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if project_id:
            rows = self.conn.execute(
                "SELECT * FROM research_tasks WHERE project_id = ? ORDER BY created_at DESC;",
                (project_id,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM research_tasks ORDER BY created_at DESC;"
            ).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            for json_key in ("sub_topics", "search_queries", "collected_doc_ids", "steps"):
                raw = d.get(f"{json_key}_json")
                try:
                    d[json_key] = json.loads(raw) if raw else []
                except Exception:
                    d[json_key] = []
            d["task_id"] = d["id"]
            d["collected_count"] = len(d["collected_doc_ids"])
            results.append(d)
        return results

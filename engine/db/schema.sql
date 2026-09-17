-- Loomark Database Schema (SQLite 3 + FTS5)
-- Core tables for Projects, Targets, Crawl Jobs, URLs, Snapshots, Documents, Subtitles, AI Artifacts, Plugins, and Logs

-- 1. Projects
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Targets (Crawl entry points and scope config for a project)
CREATE TABLE IF NOT EXISTS targets (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'domain', -- 'page', 'path', 'domain', 'subdomain', 'regex'
    scope_regex TEXT,
    adapter_id TEXT DEFAULT 'auto',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Crawl Jobs
CREATE TABLE IF NOT EXISTS crawl_jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    target_id TEXT REFERENCES targets(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING, RUNNING, PAUSED, COMPLETED, FAILED, STOPPED
    config_json TEXT NOT NULL DEFAULT '{}',
    stats_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);

-- 4. URL Frontier (Persistent Queue)
CREATE TABLE IF NOT EXISTS urls (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    url_hash TEXT NOT NULL,
    domain TEXT NOT NULL,
    depth INTEGER NOT NULL DEFAULT 0,
    priority INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'QUEUED', -- DISCOVERED, QUEUED, FETCHING, FETCHED, PARSED, FAILED, SKIPPED
    retry_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    parent_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_urls_job_status_priority ON urls(job_id, status, priority DESC, depth ASC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_urls_job_hash ON urls(job_id, url_hash);
CREATE INDEX IF NOT EXISTS idx_urls_project_hash ON urls(project_id, url_hash);
CREATE INDEX IF NOT EXISTS idx_urls_domain ON urls(domain);

-- 5. Snapshots (Raw fetched responses and metadata)
CREATE TABLE IF NOT EXISTS snapshots (
    id TEXT PRIMARY KEY,
    url_id TEXT NOT NULL REFERENCES urls(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status_code INTEGER NOT NULL,
    headers_json TEXT DEFAULT '{}',
    raw_html_path TEXT,
    screenshot_path TEXT,
    content_hash TEXT NOT NULL,
    response_time_ms INTEGER DEFAULT 0,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_snapshots_url_id ON snapshots(url_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_content_hash ON snapshots(content_hash);

-- 6. Documents (Clean extracted structured content)
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    url_id TEXT NOT NULL REFERENCES urls(id) ON DELETE CASCADE,
    type TEXT NOT NULL DEFAULT 'article', -- article, list, video, documentation, forum, unknown
    title TEXT NOT NULL DEFAULT '',
    author TEXT DEFAULT '',
    published_at TEXT,
    text TEXT NOT NULL DEFAULT '',
    markdown TEXT NOT NULL DEFAULT '',
    language TEXT DEFAULT 'zh',
    metadata_json TEXT DEFAULT '{}',
    content_hash TEXT NOT NULL,
    change_status TEXT DEFAULT 'NEW', -- NEW, UNCHANGED, UPDATED
    diff_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_documents_project_id ON documents(project_id);
CREATE INDEX IF NOT EXISTS idx_documents_url_id ON documents(url_id);
CREATE INDEX IF NOT EXISTS idx_documents_content_hash ON documents(content_hash);

-- 7. SQLite FTS5 Full-Text Search Table for Documents
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    document_id UNINDEXED,
    title,
    text,
    markdown,
    tokenize = 'unicode61'
);

-- Triggers for FTS5 synchronization
CREATE TRIGGER IF NOT EXISTS trg_documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(document_id, title, text, markdown)
    VALUES (new.id, new.title, new.text, new.markdown);
END;

CREATE TRIGGER IF NOT EXISTS trg_documents_ad AFTER DELETE ON documents BEGIN
    DELETE FROM documents_fts WHERE document_id = old.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_documents_au AFTER UPDATE ON documents BEGIN
    DELETE FROM documents_fts WHERE document_id = old.id;
    INSERT INTO documents_fts(document_id, title, text, markdown)
    VALUES (new.id, new.title, new.text, new.markdown);
END;

-- 8. Subtitles (Transcripts from videos / podcasts)
CREATE TABLE IF NOT EXISTS subtitles (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    language TEXT NOT NULL DEFAULT 'zh-CN',
    source TEXT NOT NULL DEFAULT 'official', -- official, auto, asr
    format TEXT NOT NULL DEFAULT 'json',
    segments_json TEXT NOT NULL DEFAULT '[]', -- [ { "start": 0.0, "end": 2.5, "text": "..." } ]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. AI Artifacts
CREATE TABLE IF NOT EXISTS ai_artifacts (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type TEXT NOT NULL, -- summary, tags, classification, entity, report, change_summary
    model TEXT NOT NULL,
    provider TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    result_json TEXT NOT NULL DEFAULT '{}',
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_artifacts_doc ON ai_artifacts(document_id);
CREATE INDEX IF NOT EXISTS idx_ai_artifacts_project ON ai_artifacts(project_id);

-- 10. AI Cache (Hash-based cache to eliminate redundant LLM token costs)
CREATE TABLE IF NOT EXISTS ai_cache (
    cache_key TEXT PRIMARY KEY, -- sha256(content_hash + prompt_version + model)
    result_json TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. Plugins (Site adapters and custom extractor rules)
CREATE TABLE IF NOT EXISTS plugins (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0.0',
    type TEXT NOT NULL DEFAULT 'rule', -- 'rule', 'python'
    manifest_json TEXT NOT NULL DEFAULT '{}',
    is_builtin INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. Crawl Logs
CREATE TABLE IF NOT EXISTS crawl_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'INFO', -- DEBUG, INFO, WARNING, ERROR
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_crawl_logs_job_id ON crawl_logs(job_id, id DESC);

-- 13. Website Monitoring Schedules (PRD Section 75-77, 104)
CREATE TABLE IF NOT EXISTS monitor_schedules (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    target_id TEXT REFERENCES targets(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    interval_minutes INTEGER NOT NULL DEFAULT 60, -- 15, 60, 360, 1440
    schedule_type TEXT NOT NULL DEFAULT 'interval', -- 'interval' or 'cron'
    cron_expression TEXT, -- Linux 5-field crontab expression
    enabled INTEGER NOT NULL DEFAULT 1,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_monitor_schedules_enabled ON monitor_schedules(enabled, next_run_at);

-- 14. Website Monitoring Events (NEW, UPDATED, DELETED, UNCHANGED, ERROR)
CREATE TABLE IF NOT EXISTS monitor_events (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    schedule_id TEXT REFERENCES monitor_schedules(id) ON DELETE SET NULL,
    url TEXT NOT NULL,
    event_type TEXT NOT NULL, -- NEW, UPDATED, UNCHANGED, DELETED, ERROR
    old_content_hash TEXT,
    new_content_hash TEXT,
    ai_change_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_monitor_events_project ON monitor_events(project_id, created_at DESC);

-- 15. Document Chunks (PRD Section 45, 52)
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    char_count INTEGER NOT NULL DEFAULT 0,
    token_count INTEGER NOT NULL DEFAULT 0,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_chunks_project ON chunks(project_id);

-- 16. Document Embeddings (PRD Section 42, 61, 74)
CREATE TABLE IF NOT EXISTS document_embeddings (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    model TEXT NOT NULL,
    vector_json TEXT NOT NULL, -- JSON array of floats
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_doc_embeddings ON document_embeddings(document_id, model);
CREATE INDEX IF NOT EXISTS idx_doc_embeddings_project ON document_embeddings(project_id);

-- 17. Research Tasks
CREATE TABLE IF NOT EXISTS research_tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'INITIALIZING',
    max_pages INTEGER NOT NULL DEFAULT 5,
    max_rounds INTEGER NOT NULL DEFAULT 3,
    min_relevance INTEGER NOT NULL DEFAULT 60,
    sub_topics_json TEXT NOT NULL DEFAULT '[]',
    search_queries_json TEXT NOT NULL DEFAULT '[]',
    collected_doc_ids_json TEXT NOT NULL DEFAULT '[]',
    steps_json TEXT NOT NULL DEFAULT '[]',
    final_report TEXT,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_research_tasks_project ON research_tasks(project_id, created_at DESC);

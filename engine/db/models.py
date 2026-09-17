from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = ""

class ProjectOut(BaseModel):
    id: str
    name: str
    description: str = ""
    created_at: str
    updated_at: str
    target_count: int = 0
    document_count: int = 0
    storage_bytes: int = 0

class TargetCreate(BaseModel):
    project_id: str
    url: str
    scope: str = "domain" # page, path, domain, subdomain, regex
    scope_regex: Optional[str] = None
    adapter_id: str = "auto"

class TargetOut(BaseModel):
    id: str
    project_id: str
    url: str
    scope: str
    scope_regex: Optional[str] = None
    adapter_id: str = "auto"
    created_at: str

class CrawlJobConfig(BaseModel):
    scope: str = "domain" # page, path, domain, subdomain, regex
    scope_regex: Optional[str] = None
    max_depth: int = 2
    max_pages: int = 100
    preset: str = "balanced" # gentle, balanced, fast, custom
    max_concurrent: int = 10
    domain_concurrent: int = 3
    domain_delay_ms: int = 500
    fetch_mode: str = "smart" # fast, smart, browser
    content_types: List[str] = ["article", "markdown"]
    adapter_id: str = "auto"
    enable_ai_summary: bool = False
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None

class CrawlJobCreate(BaseModel):
    project_id: str
    target_id: Optional[str] = None
    name: str
    urls: List[str] = Field(default_factory=list)
    config: CrawlJobConfig = Field(default_factory=CrawlJobConfig)

class CrawlJobOut(BaseModel):
    id: str
    project_id: str
    target_id: Optional[str] = None
    name: str
    status: str
    config_json: str
    stats_json: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

class DocumentOut(BaseModel):
    id: str
    snapshot_id: str
    project_id: str
    url_id: str
    url: Optional[str] = ""
    domain: Optional[str] = ""
    type: str = "article"
    title: str = ""
    author: Optional[str] = ""
    published_at: Optional[str] = None
    text: str = ""
    markdown: str = ""
    language: str = "zh"
    metadata_json: str = "{}"
    content_hash: str = ""
    change_status: str = "NEW"
    diff_summary: Optional[str] = None
    created_at: str

class AIArtifactOut(BaseModel):
    id: str
    document_id: str
    project_id: str
    type: str
    model: str
    provider: str
    prompt_version: str
    result_json: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    created_at: str

class CrawlLogOut(BaseModel):
    id: int
    job_id: str
    level: str
    message: str
    timestamp: str

class StatsSummary(BaseModel):
    discovered: int = 0
    queued: int = 0
    fetching: int = 0
    fetched: int = 0
    parsed: int = 0
    failed: int = 0
    skipped: int = 0
    pages_per_second: float = 0.0

export interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  target_count: number;
  document_count: number;
  storage_bytes?: number;
}

export interface Target {
  id: string;
  project_id: string;
  url: string;
  scope: "page" | "path" | "domain" | "subdomain" | "regex";
  scope_regex?: string;
  adapter_id: string;
  created_at: string;
}

export interface CrawlJobConfig {
  scope: string;
  scope_regex?: string;
  max_depth: number;
  max_pages: number;
  preset: "gentle" | "balanced" | "fast" | "custom";
  max_concurrent: number;
  domain_concurrent: number;
  domain_delay_ms: number;
  fetch_mode: "fast" | "smart" | "browser";
  content_types: string[];
  adapter_id: string;
  enable_ai_summary: boolean;
  ai_provider?: string;
  ai_model?: string;
}

export interface CrawlJob {
  id: string;
  project_id: string;
  target_id?: string;
  name: string;
  status: "PENDING" | "RUNNING" | "PAUSED" | "COMPLETED" | "FAILED" | "STOPPED";
  config_json: string;
  stats_json: string;
  created_at: string;
  started_at?: string;
  finished_at?: string;
}

export interface JobStats {
  discovered: number;
  queued: number;
  fetching: number;
  fetched: number;
  parsed: number;
  failed: number;
  skipped: number;
  pages_per_second: number;
  total?: number;
}

export interface DocumentItem {
  id: string;
  snapshot_id: string;
  project_id: string;
  url_id: string;
  url: string;
  domain: string;
  type: string;
  title: string;
  author: string;
  published_at?: string;
  text: string;
  markdown: string;
  language: string;
  metadata_json: string;
  content_hash: string;
  change_status: "NEW" | "UNCHANGED" | "UPDATED";
  diff_summary?: string;
  created_at: string;
  status_code?: number;
  raw_html_path?: string;
  fetched_at?: string;
  search_score?: number;
}


export interface SnapshotHistoryItem {
  id: string;
  url_id: string;
  status_code: number;
  content_hash: string;
  fetched_at: string;
  doc_id?: string;
  title?: string;
  change_status?: string;
  diff_summary?: string;
}

export interface AIArtifact {
  id: string;
  document_id: string;
  project_id: string;
  type: string;
  model: string;
  provider: string;
  prompt_version: string;
  result_json: any;
  input_tokens: number;
  output_tokens: number;
  cost: number;
  created_at: string;
}

export interface CrawlLog {
  level: "INFO" | "WARNING" | "ERROR" | "DEBUG";
  message: string;
  timestamp: string;
}

export interface SiteInspectionResult {
  success: boolean;
  url?: string;
  status_code?: number;
  response_time_ms?: number;
  title?: string;
  author?: string;
  detected_type?: string;
  needs_browser?: boolean;
  feed_count?: number;
  discovered_links_sample?: string[];
  total_links_found?: number;
  error?: string;
}

export interface ProjectAICosts {
  artifact_count: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost: number;
}

export interface PluginItem {
  id: string;
  name: string;
  version: string;
  type: string;
  author: string;
  match: string[];
  category: string[];
  description: string;
  rules?: Record<string, string>;
  is_builtin?: boolean;
  enabled: boolean;
}

export interface SubtitleSegment {
  start: number;
  end: number;
  text: string;
}

export interface SubtitleItem {
  id: string;
  document_id: string;
  language: string;
  source: string;
  segments_json: string;
}

export interface MonitorSchedule {
  id: string;
  project_id: string;
  target_id?: string;
  name: string;
  url: string;
  interval_minutes: number;
  schedule_type?: "interval" | "cron";
  cron_expression?: string;
  enabled: boolean;
  last_run_at?: string;
  next_run_at?: string;
  created_at: string;
}

export interface CronValidationResult {
  valid: boolean;
  description?: string;
  next_runs?: string[];
  error?: string;
}

export interface SelectorRepairResult {
  success: boolean;
  is_degraded: boolean;
  failed_fields: string[];
  old_rules?: Record<string, string>;
  suggested_rules?: Record<string, string>;
  repair_reason?: string;
  confidence?: number;
  preview_before?: any;
  preview_after?: any;
  error?: string;
}

export interface ResearchStep {
  timestamp: string;
  stage: string;
  message: string;
  detail?: any;
}

export interface ResearchTask {
  task_id: string;
  project_id: string;
  topic: string;
  status: "INITIALIZING" | "PLANNING" | "COLLECTING" | "EVALUATING" | "GAP_ANALYSIS" | "REPORTING" | "COMPLETED" | "STOPPED" | "FAILED";
  steps: ResearchStep[];
  collected_count: number;
  sub_topics: string[];
  search_queries: string[];
  final_report?: string;
  error?: string;
  created_at: string;
  finished_at?: string;
}

export interface MonitorEvent {
  id: string;
  project_id: string;
  schedule_id?: string;
  schedule_name?: string;
  url: string;
  event_type: "NEW" | "UPDATED" | "UNCHANGED" | "DELETED" | "ERROR";
  old_content_hash?: string;
  new_content_hash?: string;
  ai_change_summary?: string;
  created_at: string;
}

export interface DiffLine {
  type: "equal" | "insert" | "delete";
  text: string;
  old_num?: number | null;
  new_num?: number | null;
}

export interface DiffResult {
  has_diff: boolean;
  message?: string;
  previous_date?: string;
  current_date?: string;
  diff_lines: DiffLine[];
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  project_id: string;
  chunk_index: number;
  text: string;
  char_count: number;
  token_count: number;
  summary?: string;
  created_at: string;
}

export interface PresetPluginItem {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  match: string[];
  category: string[];
  capabilities: Record<string, boolean>;
  permissions: string[];
  rules: Record<string, string>;
}



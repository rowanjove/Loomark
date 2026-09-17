import {
  Project, Target, CrawlJob, DocumentItem, DocumentChunk, PresetPluginItem,
  SiteInspectionResult, ProjectAICosts, CrawlLog, JobStats,
  CronValidationResult, SelectorRepairResult, ResearchTask
} from "../types";


const DEFAULT_PORT = "8765";
const getResolvedHost = () => {
  if (typeof window !== "undefined" && window.location && window.location.hostname) {
    const host = window.location.hostname.toLowerCase();
    if (!host || host === "tauri.localhost" || host === "localhost") {
      return "127.0.0.1";
    }
    return host;
  }
  return "127.0.0.1";
};

export const API_BASE = `http://${getResolvedHost()}:${DEFAULT_PORT}`;
export const WS_BASE = `ws://${getResolvedHost()}:${DEFAULT_PORT}`;

export const api = {
  // Health
  checkHealth: async (): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      return res.ok;
    } catch {
      return false;
    }
  },

  // Projects
  getProjects: async (): Promise<Project[]> => {
    const res = await fetch(`${API_BASE}/api/projects`);
    if (!res.ok) throw new Error("Failed to fetch projects");
    return res.json();
  },

  createProject: async (name: string, description: string = ""): Promise<Project> => {
    const res = await fetch(`${API_BASE}/api/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description })
    });
    if (!res.ok) throw new Error("Failed to create project");
    return res.json();
  },

  getProject: async (projectId: string): Promise<Project> => {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}`);
    if (!res.ok) throw new Error("Failed to get project");
    return res.json();
  },

  deleteProject: async (projectId: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete project");
  },

  // Targets
  getTargets: async (projectId: string): Promise<Target[]> => {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/targets`);
    if (!res.ok) throw new Error("Failed to fetch targets");
    return res.json();
  },

  createTarget: async (target: { project_id: string; url: string; scope: string; scope_regex?: string; adapter_id?: string }): Promise<Target> => {
    const res = await fetch(`${API_BASE}/api/projects/${target.project_id}/targets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(target)
    });
    if (!res.ok) throw new Error("Failed to create target");
    return res.json();
  },

  // Crawl Jobs
  createCrawlJob: async (data: {
    project_id: string;
    target_id?: string;
    name: string;
    urls: string[];
    config: any;
  }): Promise<CrawlJob> => {
    const res = await fetch(`${API_BASE}/api/crawls`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error("Failed to create crawl job");
    return res.json();
  },

  getCrawlJobs: async (projectId?: string): Promise<CrawlJob[]> => {
    const url = projectId ? `${API_BASE}/api/crawls?project_id=${projectId}` : `${API_BASE}/api/crawls`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch jobs");
    return res.json();
  },

  getCrawlJob: async (jobId: string): Promise<CrawlJob> => {
    const res = await fetch(`${API_BASE}/api/crawls/${jobId}`);
    if (!res.ok) throw new Error("Failed to get crawl job");
    return res.json();
  },

  pauseCrawlJob: async (jobId: string) => {
    await fetch(`${API_BASE}/api/crawls/${jobId}/pause`, { method: "POST" });
  },

  resumeCrawlJob: async (jobId: string) => {
    await fetch(`${API_BASE}/api/crawls/${jobId}/resume`, { method: "POST" });
  },

  stopCrawlJob: async (jobId: string) => {
    await fetch(`${API_BASE}/api/crawls/${jobId}/stop`, { method: "POST" });
  },

  retryCrawlJob: async (jobId: string) => {
    const res = await fetch(`${API_BASE}/api/crawls/${jobId}/retry`, { method: "POST" });
    return res.json();
  },

  getCrawlLogs: async (jobId: string, limit: number = 100): Promise<{ id: number; level: string; message: string; timestamp: string }[]> => {
    const res = await fetch(`${API_BASE}/api/crawls/${jobId}/logs?limit=${limit}`);
    if (!res.ok) return [];
    return res.json();
  },

  // Documents & Hybrid Search
  getDocuments: async (params: {
    projectId: string;
    search?: string;
    searchMode?: "fts" | "semantic" | "hybrid";
    domain?: string;
    docType?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ items: DocumentItem[]; total: number; search_mode?: string }> => {
    const query = new URLSearchParams();
    if (params.search) query.set("search", params.search);
    if (params.searchMode) query.set("search_mode", params.searchMode);
    if (params.domain) query.set("domain", params.domain);
    if (params.docType) query.set("doc_type", params.docType);
    if (params.limit) query.set("limit", params.limit.toString());
    if (params.offset) query.set("offset", params.offset.toString());

    const res = await fetch(`${API_BASE}/api/projects/${params.projectId}/documents?${query.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch documents");
    return res.json();
  },

  getDocument: async (docId: string): Promise<DocumentItem> => {
    const res = await fetch(`${API_BASE}/api/documents/${docId}`);
    if (!res.ok) throw new Error("Failed to get document");
    return res.json();
  },

  getDocumentChunks: async (docId: string): Promise<DocumentChunk[]> => {
    const res = await fetch(`${API_BASE}/api/documents/${docId}/chunks`);
    if (!res.ok) return [];
    return res.json();
  },


  getDocumentHistory: async (docId: string) => {
    const res = await fetch(`${API_BASE}/api/documents/${docId}/history`);
    if (!res.ok) return [];
    return res.json();
  },

  getDocumentAIArtifacts: async (docId: string) => {
    const res = await fetch(`${API_BASE}/api/documents/${docId}/ai`);
    if (!res.ok) return [];
    return res.json();
  },

  triggerDocumentAI: async (docId: string, taskType: string = "article_summary_v1") => {
    const res = await fetch(`${API_BASE}/api/documents/${docId}/ai`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_type: taskType })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "AI task failed");
    }
    return res.json();
  },

  // Quick Inspector
  inspectUrl: async (url: string): Promise<SiteInspectionResult> => {
    const res = await fetch(`${API_BASE}/api/inspect-url`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    });
    return res.json();
  },

  // Export
  exportProject: async (projectId: string, format: string = "markdown", docIds?: string[]) => {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ format, doc_ids: docIds })
    });
    if (!res.ok) throw new Error("Export failed");
    return res.json();
  },

  // Settings & Costs
  getSettings: async () => {
    const res = await fetch(`${API_BASE}/api/settings`);
    return res.json();
  },

  updateSettings: async (settings: any) => {
    const res = await fetch(`${API_BASE}/api/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings)
    });
    return res.json();
  },

  getProjectCosts: async (projectId: string): Promise<ProjectAICosts> => {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/costs`);
    if (!res.ok) return { artifact_count: 0, total_input_tokens: 0, total_output_tokens: 0, total_cost: 0 };
    return res.json();
  },

  // Subtitles
  getDocumentSubtitles: async (docId: string): Promise<any[]> => {
    const res = await fetch(`${API_BASE}/api/documents/${docId}/subtitles`);
    if (!res.ok) return [];
    return res.json();
  },

  // Document Diff
  getDocumentDiff: async (docId: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/documents/${docId}/diff`);
    if (!res.ok) return { has_diff: false, diff_lines: [] };
    return res.json();
  },

  // Plugins
  getPlugins: async (): Promise<any[]> => {
    const res = await fetch(`${API_BASE}/api/plugins`);
    if (!res.ok) return [];
    return res.json();
  },

  createPlugin: async (pluginData: any): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/plugins`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(pluginData)
    });
    if (!res.ok) throw new Error("Failed to create plugin");
    return res.json();
  },

  togglePlugin: async (pluginId: string, enabled: boolean): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/plugins/${pluginId}/toggle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled })
    });
    return res.json();
  },

  deletePlugin: async (pluginId: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/plugins/${pluginId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete plugin");
    return res.json();
  },

  getPresetPlugins: async (): Promise<PresetPluginItem[]> => {
    const res = await fetch(`${API_BASE}/api/plugins/presets`);
    if (!res.ok) return [];
    return res.json();
  },

  installPresetPlugin: async (presetId: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/plugins/presets/${presetId}/install`, {
      method: "POST"
    });
    if (!res.ok) throw new Error("Failed to install preset plugin");
    return res.json();
  },

  exportPlugin: async (pluginId: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/plugins/${pluginId}/export`);
    if (!res.ok) throw new Error("Failed to export plugin");
    return res.json();
  },

  importPlugin: async (pluginData: any): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/plugins/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(pluginData)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to import plugin");
    }
    return res.json();
  },


  testRule: async (url: string, rules: Record<string, string>, html?: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/plugins/test-rule`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, rules, html })
    });
    return res.json();
  },

  // Monitoring
  getMonitorSchedules: async (projectId?: string): Promise<any[]> => {
    const query = projectId ? `?project_id=${projectId}` : "";
    const res = await fetch(`${API_BASE}/api/monitoring/schedules${query}`);
    if (!res.ok) return [];
    return res.json();
  },

  createMonitorSchedule: async (data: {
    project_id: string;
    name: string;
    url: string;
    interval_minutes: number;
    target_id?: string;
    schedule_type?: "interval" | "cron";
    cron_expression?: string;
  }): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/monitoring/schedules`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error("Failed to create monitor schedule");
    return res.json();
  },

  toggleMonitorSchedule: async (scheduleId: string, enabled: boolean): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/monitoring/schedules/${scheduleId}/toggle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled })
    });
    return res.json();
  },

  deleteMonitorSchedule: async (scheduleId: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/monitoring/schedules/${scheduleId}`, { method: "DELETE" });
    return res.json();
  },

  getMonitorEvents: async (projectId?: string, limit: number = 50): Promise<any[]> => {
    const query = new URLSearchParams();
    if (projectId) query.set("project_id", projectId);
    query.set("limit", limit.toString());
    const res = await fetch(`${API_BASE}/api/monitoring/events?${query.toString()}`);
    if (!res.ok) return [];
    return res.json();
  },

  // Project Report
  generateProjectReport: async (projectId: string, model?: string): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/projects/${projectId}/generate-report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "生成项目研报失败");
    }
    return res.json();
  },

  // Clear Storage Cache
  clearCache: async (): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/storage/clear-cache`, { method: "POST" });
    return res.json();
  },

  // Cron Validation
  validateCron: async (expression: string): Promise<CronValidationResult> => {
    const res = await fetch(`${API_BASE}/api/monitoring/validate-cron`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expression })
    });
    return res.json();
  },

  // Selector Auto-Repair (PRD Section 30)
  diagnoseSelectorRepair: async (pluginId: string, url: string, html?: string): Promise<SelectorRepairResult> => {
    const res = await fetch(`${API_BASE}/api/plugins/${pluginId}/diagnose-repair`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, html })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "诊断修复失败");
    }
    return res.json();
  },

  applySelectorRepair: async (pluginId: string, suggestedRules: Record<string, string>): Promise<any> => {
    const res = await fetch(`${API_BASE}/api/plugins/${pluginId}/apply-repair`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ suggested_rules: suggestedRules })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "应用修复规则失败");
    }
    return res.json();
  },

  // Research Agent (PRD Section 49 & 105)
  startResearchTask: async (data: {
    project_id: string;
    topic: string;
    max_pages?: number;
    max_rounds?: number;
    min_relevance?: number;
  }): Promise<ResearchTask> => {
    const res = await fetch(`${API_BASE}/api/research/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "启动自主研究任务失败");
    }
    return res.json();
  },

  getResearchTasks: async (projectId?: string): Promise<ResearchTask[]> => {
    const query = projectId ? `?project_id=${projectId}` : "";
    const res = await fetch(`${API_BASE}/api/research/tasks${query}`);
    if (!res.ok) return [];
    return res.json();
  },

  getResearchTask: async (taskId: string): Promise<ResearchTask> => {
    const res = await fetch(`${API_BASE}/api/research/tasks/${taskId}`);
    if (!res.ok) throw new Error("获取研究任务详情失败");
    return res.json();
  },

  stopResearchTask: async (taskId: string): Promise<{ success: boolean }> => {
    const res = await fetch(`${API_BASE}/api/research/tasks/${taskId}/stop`, { method: "POST" });
    return res.json();
  }
};

// WebSocket Hook Helper for live crawl job monitoring with exponential backoff reconnect
export function subscribeToCrawlJob(
  jobId: string,
  onStats: (stats: JobStats) => void,
  onLog: (log: CrawlLog) => void
): () => void {
  let ws: WebSocket | null = null;
  let isClosedManually = false;
  let retryCount = 0;
  let reconnectTimer: any = null;
  let pingInterval: any = null;

  const connect = () => {
    if (isClosedManually) return;
    try {
      ws = new WebSocket(`${WS_BASE}/ws/crawls/${jobId}`);

      ws.onopen = () => {
        retryCount = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === "stats") {
            onStats(message.data);
          } else if (message.type === "log") {
            onLog(message.data);
          }
        } catch {}
      };

      ws.onclose = () => {
        if (!isClosedManually) {
          const delay = Math.min(1000 * Math.pow(2, retryCount), 8000);
          retryCount++;
          reconnectTimer = setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        try {
          ws?.close();
        } catch {}
      };
    } catch {
      if (!isClosedManually) {
        reconnectTimer = setTimeout(connect, 2000);
      }
    }
  };

  connect();

  pingInterval = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send("ping");
    }
  }, 5000);

  return () => {
    isClosedManually = true;
    clearInterval(pingInterval);
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (ws) {
      try {
        ws.close();
      } catch {}
    }
  };
}

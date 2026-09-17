import React, { useState, useEffect } from "react";
import { Project, Target, CrawlJob, DocumentItem, ProjectAICosts } from "../../types";
import { api } from "../../services/api";
import { DocumentTable } from "../documents/DocumentTable";
import {
  FolderKanban, Activity, FileText, Globe, Cpu,
  Plus, Play, ArrowLeft, Download, RefreshCw, Clock, Sparkles, Copy, Check, BookOpen
} from "lucide-react";

interface ProjectDetailProps {
  project: Project;
  onBack: () => void;
  onStartCrawl: (project: Project) => void;
  onSelectJob: (jobId: string) => void;
  onSelectDocument: (doc: DocumentItem) => void;
  onOpenExport: (selectedDocIds?: string[]) => void;
  onOpenGuide?: () => void;
}

type DetailTab = "overview" | "crawls" | "documents" | "sources" | "ai";

export const ProjectDetail: React.FC<ProjectDetailProps> = ({
  project,
  onBack,
  onStartCrawl,
  onSelectJob,
  onSelectDocument,
  onOpenExport,
  onOpenGuide
}) => {
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [jobs, setJobs] = useState<CrawlJob[]>([]);
  const [targets, setTargets] = useState<Target[]>([]);
  const [costs, setCosts] = useState<ProjectAICosts | null>(null);
  const [loading, setLoading] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [projectReport, setProjectReport] = useState<string | null>(null);
  const [copiedReport, setCopiedReport] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [fetchedJobs, fetchedTargets, fetchedCosts] = await Promise.all([
        api.getCrawlJobs(project.id),
        api.getTargets(project.id),
        api.getProjectCosts(project.id)
      ]);
      setJobs(fetchedJobs);
      setTargets(fetchedTargets);
      setCosts(fetchedCosts);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [project.id]);

  const tabs: { id: DetailTab; label: string; icon: React.ReactNode }[] = [
    { id: "overview", label: "概览", icon: <FolderKanban size={14} /> },
    { id: "crawls", label: `采集任务 (${jobs.length})`, icon: <Activity size={14} /> },
    { id: "documents", label: "文档归档库", icon: <FileText size={14} /> },
    { id: "sources", label: `数据源 (${targets.length})`, icon: <Globe size={14} /> },
    { id: "ai", label: "AI 研报统计", icon: <Cpu size={14} /> },
  ];

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-zinc-950">
      {/* Detail Header */}
      <div className="h-16 border-b border-zinc-800/80 px-6 flex items-center justify-between shrink-0 bg-zinc-900/50">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-1.5 text-zinc-400 hover:text-zinc-100 rounded-md hover:bg-zinc-800 transition-colors"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <h1 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
              <span>{project.name}</span>
            </h1>
            <p className="text-xs text-zinc-400 truncate max-w-xl">
              {project.description || "暂无项目描述"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {onOpenGuide && (
            <button
              onClick={onOpenGuide}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-emerald-500/50 text-zinc-300 hover:text-zinc-100 text-xs font-medium rounded-md transition-colors"
            >
              <BookOpen size={13} className="text-emerald-400" />
              <span>使用教程</span>
            </button>
          )}

          <button
            onClick={() => onOpenExport()}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-zinc-100 text-xs font-medium rounded-md transition-colors"
          >
            <Download size={13} />
            <span>全量导出</span>
          </button>

          <button
            onClick={() => onStartCrawl(project)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-zinc-100 text-zinc-900 hover:bg-white text-xs font-semibold rounded-md shadow-xs transition-all active:scale-95"
          >
            <Play size={12} className="fill-zinc-900 stroke-none" />
            <span>发起新采集</span>
          </button>
        </div>
      </div>

      {/* Sub Navigation Tabs */}
      <div className="h-11 border-b border-zinc-800/80 px-6 flex items-center gap-1 shrink-0 select-none bg-zinc-950">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-zinc-800 text-zinc-100 font-semibold"
                : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Contents */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 1. Overview */}
        {activeTab === "overview" && (
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-zinc-900/60 border border-zinc-800 rounded-lg">
                <div className="text-xs text-zinc-400 mb-1">已采集归档文档</div>
                <div className="text-2xl font-semibold font-mono text-zinc-100">{project.document_count} 篇</div>
              </div>

              <div className="p-4 bg-zinc-900/60 border border-zinc-800 rounded-lg">
                <div className="text-xs text-zinc-400 mb-1">已执行采集任务</div>
                <div className="text-2xl font-semibold font-mono text-zinc-100">{jobs.length} 次</div>
              </div>

              <div className="p-4 bg-zinc-900/60 border border-zinc-800 rounded-lg">
                <div className="text-xs text-zinc-400 mb-1">AI 研报消耗预估</div>
                <div className="text-2xl font-semibold font-mono text-purple-400">
                  ${costs ? costs.total_cost.toFixed(4) : "0.0000"}
                </div>
              </div>
            </div>

            {/* Recent Crawl Jobs */}
            <div className="p-5 bg-zinc-900/40 border border-zinc-800 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-zinc-200">最近采集记录</h3>
                <button onClick={() => setActiveTab("crawls")} className="text-xs text-zinc-400 hover:text-zinc-200">
                  查看全部
                </button>
              </div>

              <div className="divide-y divide-zinc-800/60">
                {jobs.slice(0, 5).map((job) => (
                  <div
                    key={job.id}
                    onClick={() => onSelectJob(job.id)}
                    className="py-3 flex items-center justify-between hover:bg-zinc-900/60 px-2 rounded cursor-pointer transition-colors"
                  >
                    <div>
                      <div className="text-xs font-medium text-zinc-200">{job.name}</div>
                      <div className="text-[11px] text-zinc-500 font-mono mt-0.5">创建于 {job.created_at}</div>
                    </div>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                      job.status === "RUNNING" ? "bg-emerald-500/10 text-emerald-400" :
                      job.status === "COMPLETED" ? "bg-sky-500/10 text-sky-400" :
                      "bg-zinc-800 text-zinc-400"
                    }`}>
                      {job.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 2. Crawls List */}
        {activeTab === "crawls" && (
          <div className="flex-1 overflow-y-auto p-6 space-y-3">
            {jobs.length === 0 ? (
              <div className="text-center py-16 text-zinc-500 text-xs">
                暂未发起采集任务，点击右上角 "发起新采集" 开始。
              </div>
            ) : (
              jobs.map((job) => (
                <div
                  key={job.id}
                  onClick={() => onSelectJob(job.id)}
                  className="p-4 bg-zinc-900/60 hover:bg-zinc-900 border border-zinc-800 rounded-lg flex items-center justify-between cursor-pointer transition-all shadow-xs"
                >
                  <div>
                    <div className="flex items-center gap-2.5">
                      <span className="text-sm font-semibold text-zinc-100">{job.name}</span>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                        job.status === "RUNNING" ? "bg-emerald-500/10 text-emerald-400" :
                        job.status === "COMPLETED" ? "bg-sky-500/10 text-sky-400" :
                        "bg-zinc-800 text-zinc-400"
                      }`}>
                        {job.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-zinc-500 font-mono mt-2">
                      <span>ID: {job.id.slice(0, 8)}</span>
                      <span>创建: {job.created_at}</span>
                      {job.finished_at && <span>完成: {job.finished_at}</span>}
                    </div>
                  </div>

                  <button className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-200 rounded font-medium">
                    进入监控面板
                  </button>
                </div>
              ))
            )}
          </div>
        )}

        {/* 3. Documents Table */}
        {activeTab === "documents" && (
          <DocumentTable
            projectId={project.id}
            onSelectDocument={onSelectDocument}
            onOpenExport={onOpenExport}
          />
        )}

        {/* 4. Sources */}
        {activeTab === "sources" && (
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            <h3 className="text-xs font-semibold text-zinc-300">已配置采集目标源 (Targets)</h3>
            <div className="space-y-2">
              {targets.map((t) => (
                <div key={t.id} className="p-3 bg-zinc-900/60 border border-zinc-800 rounded flex items-center justify-between text-xs">
                  <div className="font-mono text-zinc-200">{t.url}</div>
                  <div className="text-zinc-500 font-mono text-[11px]">Scope: {t.scope}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 5. AI Costs & Project Report */}
        {activeTab === "ai" && (
          <div className="flex-1 overflow-y-auto p-6 max-w-3xl space-y-6">
            {/* Global Report Generator Card */}
            <div className="p-5 bg-zinc-900 border border-zinc-800 rounded-xl space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Sparkles size={18} className="text-purple-400" />
                  <div>
                    <h3 className="text-sm font-semibold text-zinc-100">项目综合研究分析报告 (Project Summary Report)</h3>
                    <p className="text-xs text-zinc-400 mt-0.5">跨文档聚合已归档资料，提炼行业趋势、核心观点与结构化洞察</p>
                  </div>
                </div>
                <button
                  onClick={async () => {
                    setGeneratingReport(true);
                    try {
                      const res = await api.generateProjectReport(project.id);
                      const text = res.result?.text || JSON.stringify(res.result);
                      setProjectReport(text);
                      loadData();
                    } catch (e: any) {
                      alert(e.message);
                    } finally {
                      setGeneratingReport(false);
                    }
                  }}
                  disabled={generatingReport || project.document_count === 0}
                  className="px-3.5 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold rounded-md shadow-xs transition-all flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Sparkles size={13} />
                  <span>{generatingReport ? "研报合成中..." : "一键生成项目综合研报"}</span>
                </button>
              </div>

              {projectReport && (
                <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-lg space-y-2">
                  <div className="flex items-center justify-between border-b border-zinc-800 pb-2">
                    <span className="text-xs font-semibold text-purple-300">《{project.name}》综合分析研报</span>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(projectReport);
                        setCopiedReport(true);
                        setTimeout(() => setCopiedReport(false), 2000);
                      }}
                      className="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1"
                    >
                      {copiedReport ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                      <span>{copiedReport ? "已复制" : "复制报告"}</span>
                    </button>
                  </div>
                  <div className="text-xs text-zinc-200 leading-relaxed whitespace-pre-wrap font-sans select-text max-h-[40vh] overflow-y-auto">
                    {projectReport}
                  </div>
                </div>
              )}
            </div>

            {/* AI Costs */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-zinc-200">AI 消耗统计 (Token Accounting)</h3>
              <div className="p-5 bg-zinc-900/60 border border-zinc-800 rounded-xl space-y-3 text-xs">
                <div className="flex justify-between py-1 border-b border-zinc-800/80">
                  <span className="text-zinc-400">已生成 AI 研报条目</span>
                  <span className="font-mono font-medium text-zinc-100">{costs?.artifact_count || 0}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-zinc-800/80">
                  <span className="text-zinc-400">输入 Prompt Tokens</span>
                  <span className="font-mono font-medium text-zinc-100">{(costs?.total_input_tokens || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-zinc-800/80">
                  <span className="text-zinc-400">输出 Completion Tokens</span>
                  <span className="font-mono font-medium text-zinc-100">{(costs?.total_output_tokens || 0).toLocaleString()}</span>
                </div>
                <div className="flex justify-between py-1 text-sm font-semibold pt-2">
                  <span className="text-zinc-200">预估总费用</span>
                  <span className="font-mono text-purple-400">${(costs?.total_cost || 0).toFixed(4)} USD</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

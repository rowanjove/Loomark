import React, { useState, useEffect } from "react";
import { Project, ResearchTask, ResearchStep } from "../../types";
import { api } from "../../services/api";
import {
  Compass, Play, Square, Sparkles, CheckCircle2, AlertCircle,
  Clock, RefreshCw, FileText, Globe, Layers, ArrowRight, ExternalLink
} from "lucide-react";

interface ResearchViewProps {
  projects: Project[];
}

export const ResearchView: React.FC<ResearchViewProps> = ({ projects }) => {
  const [tasks, setTasks] = useState<ResearchTask[]>([]);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [activeTask, setActiveTask] = useState<ResearchTask | null>(null);
  const [loading, setLoading] = useState(false);

  // Form State
  const [selectedProjectId, setSelectedProjectId] = useState<string>(projects[0]?.id || "");
  const [topic, setTopic] = useState("");
  const [maxPages, setMaxPages] = useState(5);
  const [maxRounds, setMaxRounds] = useState(3);
  const [minRelevance, setMinRelevance] = useState(65);
  const [starting, setStarting] = useState(false);

  const loadTasks = async () => {
    try {
      const data = await api.getResearchTasks();
      setTasks(data);
      if (!activeTaskId && data.length > 0) {
        setActiveTaskId(data[0].task_id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadTasks();
  }, []);

  // Polling active task status
  useEffect(() => {
    if (!activeTaskId) return;

    const fetchDetail = async () => {
      try {
        const detail = await api.getResearchTask(activeTaskId);
        setActiveTask(detail);
      } catch (e) {
        console.error(e);
      }
    };

    fetchDetail();
    const interval = setInterval(() => {
      fetchDetail();
      loadTasks();
    }, 2500);

    return () => clearInterval(interval);
  }, [activeTaskId]);

  const handleStartTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId || !topic.trim()) return;

    setStarting(true);
    try {
      const newTask = await api.startResearchTask({
        project_id: selectedProjectId,
        topic: topic.trim(),
        max_pages: maxPages,
        max_rounds: maxRounds,
        min_relevance: minRelevance
      });
      setActiveTaskId(newTask.task_id);
      setActiveTask(newTask);
      setTopic("");
      loadTasks();
    } catch (e: any) {
      alert(`启动自主研究失败: ${e.message}`);
    } finally {
      setStarting(false);
    }
  };

  const handleStopTask = async () => {
    if (!activeTaskId) return;
    try {
      await api.stopResearchTask(activeTaskId);
      if (activeTask) {
        setActiveTask({ ...activeTask, status: "STOPPED" });
      }
      loadTasks();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const isRunning = activeTask && ["INITIALIZING", "PLANNING", "COLLECTING", "EVALUATING", "GAP_ANALYSIS", "REPORTING"].includes(activeTask.status);

  return (
    <div className="flex-1 overflow-y-auto bg-zinc-950 p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
              <Compass size={20} className="text-purple-400" />
              <span>主题定向调研 (Research)</span>
            </h1>
            <p className="text-xs text-zinc-400 mt-1">
              输入研究课题，系统将自动分解检索关键词、评估内容相关度并生成结构化分析报告。
            </p>
          </div>

          <button
            onClick={loadTasks}
            className="p-2 text-zinc-400 hover:text-zinc-200 bg-zinc-900 border border-zinc-800 rounded-md transition-colors"
            title="刷新"
          >
            <RefreshCw size={14} />
          </button>
        </div>

        {/* Start New Research Card */}
        <section className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-zinc-800">
            <Sparkles size={16} className="text-purple-400" />
            <h3 className="text-sm font-semibold text-zinc-200">新建调研任务</h3>
          </div>

          <form onSubmit={handleStartTask} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">归档项目</label>
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-zinc-300 mb-1">调研课题 / 关键词</label>
                <input
                  type="text"
                  required
                  placeholder="如：2026 年具身智能端到端控制框架与产业进展"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4 pt-2 border-t border-zinc-800/60 text-xs text-zinc-400">
              <div>
                <label className="block text-[11px] mb-1">文献采集上限</label>
                <select
                  value={maxPages}
                  onChange={(e) => setMaxPages(Number(e.target.value))}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded px-2 py-1.5 text-xs text-zinc-200"
                >
                  <option value={3}>精炼 (3 篇文献)</option>
                  <option value={5}>标准 (5 篇文献)</option>
                  <option value={10}>详实 (10 篇文献)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] mb-1">最大检索轮次</label>
                <select
                  value={maxRounds}
                  onChange={(e) => setMaxRounds(Number(e.target.value))}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded px-2 py-1.5 text-xs text-zinc-200"
                >
                  <option value={2}>2 轮检索</option>
                  <option value={3}>3 轮检索 (推荐)</option>
                  <option value={4}>4 轮检索</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] mb-1">相关度筛选阈值</label>
                <select
                  value={minRelevance}
                  onChange={(e) => setMinRelevance(Number(e.target.value))}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded px-2 py-1.5 text-xs text-zinc-200"
                >
                  <option value={60}>60 分 (宽松)</option>
                  <option value={70}>70 分 (标准)</option>
                  <option value={80}>80 分 (严格)</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={starting || !topic.trim()}
                className="flex items-center gap-1.5 px-5 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white text-xs font-semibold rounded-md shadow-sm transition-all"
              >
                <Play size={13} className="fill-white" />
                <span>{starting ? "正在启动..." : "开始调研"}</span>
              </button>
            </div>
          </form>
        </section>

        {/* Active Research Progress & Output */}
        {activeTask ? (
          <div className="space-y-6">
            {/* Task Banner */}
            <div className="p-4 bg-zinc-900/80 border border-zinc-800 rounded-xl flex items-center justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                    activeTask.status === "COMPLETED"
                      ? "bg-emerald-950 text-emerald-300 border border-emerald-800/50"
                      : activeTask.status === "STOPPED" || activeTask.status === "FAILED"
                      ? "bg-rose-950 text-rose-300 border border-rose-800/50"
                      : "bg-purple-950 text-purple-300 border border-purple-800/50 animate-pulse"
                  }`}>
                    {activeTask.status}
                  </span>
                  <h2 className="text-sm font-bold text-zinc-100">{activeTask.topic}</h2>
                </div>
                <div className="text-[11px] font-mono text-zinc-500 flex items-center gap-3">
                  <span>已采纳文献: {activeTask.collected_count} 篇</span>
                  <span>•</span>
                  <span>创建时间: {activeTask.created_at.slice(0, 19).replace("T", " ")}</span>
                </div>
              </div>

              {isRunning && (
                <button
                  onClick={handleStopTask}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-rose-950 text-zinc-300 hover:text-rose-300 border border-zinc-700 hover:border-rose-800 rounded text-xs transition-colors"
                >
                  <Square size={13} />
                  <span>停止任务</span>
                </button>
              )}
            </div>

            {/* Main Stage Grid: Left = Thinking Stream, Right = Report / Evidence */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left: Thinking & Actions Stream */}
              <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5 space-y-3 flex flex-col h-[520px]">
                <div className="flex items-center justify-between border-b border-zinc-800 pb-2.5">
                  <span className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
                    <Layers size={14} className="text-purple-400" />
                    <span>调研执行流 (Execution Log)</span>
                  </span>
                  <span className="text-[10px] font-mono text-zinc-500">
                    {activeTask.steps.length} 个步骤
                  </span>
                </div>

                <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 text-xs">
                  {activeTask.steps.map((step, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-zinc-950/70 border border-zinc-800/70 rounded-lg space-y-1"
                    >
                      <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500">
                        <span className="px-1.5 py-0.2 rounded bg-zinc-800 text-purple-300 font-semibold">
                          {step.stage}
                        </span>
                        <span>{step.timestamp.slice(11, 19)}</span>
                      </div>
                      <p className="text-zinc-200 leading-relaxed">{step.message}</p>

                      {step.detail?.url && (
                        <div className="pt-1 text-[10px] font-mono text-zinc-400 truncate">
                          URL: {step.detail.url}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Right: Synthesis Report or Discovered Topics */}
              <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5 space-y-3 flex flex-col h-[520px]">
                <div className="flex items-center justify-between border-b border-zinc-800 pb-2.5">
                  <span className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
                    <FileText size={14} className="text-sky-400" />
                    <span>调研总结报告 (Analysis Report)</span>
                  </span>
                </div>

                <div className="flex-1 overflow-y-auto pr-1 text-xs leading-relaxed text-zinc-300">
                  {activeTask.final_report ? (
                    <div className="prose prose-invert prose-xs max-w-none space-y-3">
                      <pre className="whitespace-pre-wrap font-sans text-zinc-200 leading-relaxed p-4 bg-zinc-950/80 rounded-lg border border-zinc-800/80">
                        {activeTask.final_report}
                      </pre>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-center text-zinc-500 space-y-2 p-6">
                      <Sparkles size={24} className="text-purple-400/50 animate-pulse" />
                      <p className="text-xs">正在抓取文献并分析信息覆盖度...</p>
                      <p className="text-[11px] text-zinc-600">任务完成后将在此展示调研分析报告。</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-12 text-center bg-zinc-900/40 border border-zinc-800/80 rounded-xl text-xs text-zinc-500">
            暂无进行中的研究任务，输入课题后即可开始调研。
          </div>
        )}
      </div>
    </div>
  );
};

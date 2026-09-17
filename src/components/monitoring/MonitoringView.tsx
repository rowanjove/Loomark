import React, { useState, useEffect } from "react";
import { MonitorSchedule, MonitorEvent, Project } from "../../types";
import { api } from "../../services/api";
import {
  Eye, Plus, Clock, Play, Pause, Trash2, Globe,
  AlertCircle, CheckCircle2, RefreshCw, Sparkles, X, ChevronRight
} from "lucide-react";

interface MonitoringViewProps {
  projects: Project[];
}

export const MonitoringView: React.FC<MonitoringViewProps> = ({ projects }) => {
  const [schedules, setSchedules] = useState<MonitorSchedule[]>([]);
  const [events, setEvents] = useState<MonitorEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  // Form state
  const [selectedProjectId, setSelectedProjectId] = useState<string>(projects[0]?.id || "");
  const [schedName, setSchedName] = useState("");
  const [schedUrl, setSchedUrl] = useState("");
  const [schedType, setSchedType] = useState<"interval" | "cron">("interval");
  const [intervalMin, setIntervalMin] = useState(60);
  const [cronExpr, setCronExpr] = useState("*/15 * * * *");
  const [cronValidation, setCronValidation] = useState<{
    valid: boolean;
    description?: string;
    next_runs?: string[];
    error?: string;
  } | null>(null);

  useEffect(() => {
    if (schedType === "cron" && cronExpr.trim()) {
      const timer = setTimeout(() => {
        api.validateCron(cronExpr.trim()).then(setCronValidation).catch(() => {});
      }, 300);
      return () => clearTimeout(timer);
    } else {
      setCronValidation(null);
    }
  }, [schedType, cronExpr]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [schedList, eventList] = await Promise.all([
        api.getMonitorSchedules(),
        api.getMonitorEvents(undefined, 50)
      ]);
      setSchedules(schedList);
      setEvents(eventList);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 10000);
    return () => clearInterval(timer);
  }, []);

  const handleCreateSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId || !schedUrl.trim()) return;

    if (schedType === "cron" && cronValidation && !cronValidation.valid) {
      alert(`Cron 表达式不合法: ${cronValidation.error || "请核对语法"}`);
      return;
    }

    try {
      await api.createMonitorSchedule({
        project_id: selectedProjectId,
        name: schedName || schedUrl,
        url: schedUrl.trim(),
        interval_minutes: intervalMin,
        schedule_type: schedType,
        cron_expression: schedType === "cron" ? cronExpr.trim() : undefined
      });
      setIsCreateOpen(false);
      setSchedName("");
      setSchedUrl("");
      loadData();
    } catch (e: any) {
      alert(`创建监控计划失败: ${e.message}`);
    }
  };

  const handleToggle = async (id: string, currentEnabled: boolean) => {
    await api.toggleMonitorSchedule(id, !currentEnabled);
    loadData();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除该监控计划吗？")) return;
    await api.deleteMonitorSchedule(id);
    loadData();
  };

  return (
    <div className="flex-1 overflow-y-auto bg-zinc-950 p-8">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
              <Eye size={20} className="text-sky-400" />
              <span>网站定时监控与变动检测 (Website Monitoring)</span>
            </h1>
            <p className="text-xs text-zinc-400 mt-1">
              自动周期性巡检目标网站，精准记录内容增量变动事件，并联动 AI 生成智能变化摘要。
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={loadData}
              className="p-2 text-zinc-400 hover:text-zinc-200 bg-zinc-900 border border-zinc-800 rounded-md transition-colors"
              title="刷新数据"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            </button>
            <button
              onClick={() => setIsCreateOpen(true)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-zinc-100 text-zinc-900 hover:bg-white text-xs font-semibold rounded-md shadow-xs transition-all"
            >
              <Plus size={14} />
              <span>新建监控计划</span>
            </button>
          </div>
        </div>

        {/* 1. Monitoring Schedules Grid */}
        <section className="space-y-3">
          <div className="flex items-center justify-between text-xs text-zinc-400 font-medium">
            <span>运行中的监控计划 ({schedules.length})</span>
          </div>

          {schedules.length === 0 ? (
            <div className="p-8 text-center bg-zinc-900/40 border border-zinc-800/80 rounded-xl text-xs text-zinc-500">
              暂无配置任何监控计划，点击右上角“新建监控计划”开始巡检。
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {schedules.map((s) => (
                <div key={s.id} className="p-4 bg-zinc-900/60 border border-zinc-800 rounded-xl space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2 overflow-hidden mr-2">
                      <Globe size={15} className="text-zinc-400 shrink-0" />
                      <h3 className="text-xs font-semibold text-zinc-100 truncate" title={s.name}>
                        {s.name}
                      </h3>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => handleToggle(s.id, s.enabled)}
                        className={`p-1 rounded text-xs transition-colors ${
                          s.enabled ? "text-emerald-400 hover:bg-emerald-950/40" : "text-zinc-500 hover:bg-zinc-800"
                        }`}
                        title={s.enabled ? "点击暂停监控" : "点击启动监控"}
                      >
                        {s.enabled ? <Play size={13} className="fill-emerald-400" /> : <Pause size={13} />}
                      </button>
                      <button
                        onClick={() => handleDelete(s.id)}
                        className="p-1 text-zinc-500 hover:text-rose-400 rounded hover:bg-rose-950/20"
                        title="删除监控计划"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>

                  <div className="text-[11px] font-mono text-zinc-400 truncate" title={s.url}>
                    {s.url}
                  </div>

                  <div className="pt-2 border-t border-zinc-800/60 flex items-center justify-between text-[11px] text-zinc-500">
                    <span className="flex items-center gap-1.5">
                      <Clock size={12} />
                      {s.schedule_type === "cron" ? (
                        <span className="inline-flex items-center gap-1.5">
                          <span className="px-1.5 py-0.2 rounded bg-purple-950/70 text-purple-300 border border-purple-800/40 text-[10px] font-mono">
                            CRON
                          </span>
                          <span className="font-mono text-zinc-300">{s.cron_expression}</span>
                        </span>
                      ) : (
                        <span>巡检频率: 每 {s.interval_minutes} 分钟</span>
                      )}
                    </span>
                    <span>
                      {s.next_run_at ? `下次: ${s.next_run_at.slice(11, 19)}` : (s.last_run_at ? `上次: ${s.last_run_at.slice(11, 19)}` : "尚未运行")}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 2. Change Events Timeline */}
        <section className="space-y-4">
          <div className="flex items-center justify-between text-xs text-zinc-400 font-medium">
            <span>变动事件流 (Change Events Timeline)</span>
            <span className="text-[11px] text-zinc-500">自动同步内容哈希差异</span>
          </div>

          {events.length === 0 ? (
            <div className="p-8 text-center bg-zinc-900/40 border border-zinc-800/80 rounded-xl text-xs text-zinc-500">
              暂无变动事件记录。当监控触发并检测到内容更新时，事件将自动流式呈现于此。
            </div>
          ) : (
            <div className="space-y-2.5">
              {events.map((ev) => {
                const isUpdated = ev.event_type === "UPDATED";
                const isNew = ev.event_type === "NEW";
                const isError = ev.event_type === "ERROR";

                return (
                  <div
                    key={ev.id}
                    className="p-4 bg-zinc-900/50 border border-zinc-800/80 rounded-xl hover:border-zinc-700/80 transition-colors space-y-2"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2 overflow-hidden mr-2">
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold shrink-0 ${
                            isUpdated
                              ? "bg-amber-950/60 text-amber-300 border border-amber-800/50"
                              : isNew
                              ? "bg-emerald-950/60 text-emerald-300 border border-emerald-800/50"
                              : isError
                              ? "bg-rose-950/60 text-rose-300 border border-rose-800/50"
                              : "bg-zinc-800 text-zinc-400"
                          }`}
                        >
                          {ev.event_type}
                        </span>
                        <a
                          href={ev.url}
                          target="_blank"
                          rel="noreferrer"
                          className="font-mono text-zinc-200 hover:text-sky-300 truncate"
                        >
                          {ev.url}
                        </a>
                      </div>
                      <span className="text-[11px] font-mono text-zinc-500 shrink-0">
                        {ev.created_at}
                      </span>
                    </div>

                    {/* AI Change Summary */}
                    {ev.ai_change_summary && (
                      <div className="p-2.5 bg-zinc-950/60 border border-zinc-800/60 rounded-lg text-xs text-zinc-300 flex items-start gap-2">
                        <Sparkles size={14} className="text-purple-400 shrink-0 mt-0.5" />
                        <span className="leading-relaxed">{ev.ai_change_summary}</span>
                      </div>
                    )}

                    {/* Hash footer */}
                    {ev.old_content_hash && ev.new_content_hash && isUpdated && (
                      <div className="text-[10px] font-mono text-zinc-500 flex items-center gap-2">
                        <span>旧: {ev.old_content_hash.slice(0, 8)}...</span>
                        <ChevronRight size={11} />
                        <span>新: {ev.new_content_hash.slice(0, 8)}...</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Modal: Create Schedule */}
        {isCreateOpen && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-md p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
                <div className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
                  <Eye size={16} className="text-sky-400" />
                  <span>新建网站监控任务</span>
                </div>
                <button onClick={() => setIsCreateOpen(false)} className="text-zinc-400 hover:text-zinc-200">
                  <X size={16} />
                </button>
              </div>

              <form onSubmit={handleCreateSchedule} className="space-y-3.5">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">关联项目</label>
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

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">监控任务名称</label>
                  <input
                    type="text"
                    required
                    placeholder="如：官方产品发布页巡检"
                    value={schedName}
                    onChange={(e) => setSchedName(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">目标页面 URL</label>
                  <input
                    type="url"
                    required
                    placeholder="https://example.com/products"
                    value={schedUrl}
                    onChange={(e) => setSchedUrl(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1.5">调度巡检模式</label>
                  <div className="grid grid-cols-2 gap-2 mb-3">
                    <button
                      type="button"
                      onClick={() => setSchedType("interval")}
                      className={`py-1.5 text-xs rounded border transition-all ${
                        schedType === "interval"
                          ? "bg-zinc-800 border-zinc-600 text-zinc-100 font-semibold shadow-xs"
                          : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:text-zinc-200"
                      }`}
                    >
                      固定时间间隔
                    </button>
                    <button
                      type="button"
                      onClick={() => setSchedType("cron")}
                      className={`py-1.5 text-xs rounded border transition-all ${
                        schedType === "cron"
                          ? "bg-zinc-800 border-purple-600/80 text-purple-200 font-semibold shadow-xs"
                          : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:text-zinc-200"
                      }`}
                    >
                      Linux Crontab 表达式
                    </button>
                  </div>
                </div>

                {schedType === "interval" ? (
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">巡检周期频率</label>
                    <select
                      value={intervalMin}
                      onChange={(e) => setIntervalMin(Number(e.target.value))}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
                    >
                      <option value={15}>每 15 分钟巡检一次 (高频关注)</option>
                      <option value={60}>每 1 小时巡检一次 (推荐默认)</option>
                      <option value={360}>每 6 小时巡检一次</option>
                      <option value={1440}>每 24 小时 / 每天巡检一次</option>
                    </select>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <label className="block text-xs font-medium text-zinc-300">5 段式 Linux Crontab 表达式</label>
                    <input
                      type="text"
                      required
                      placeholder="分 时 日 月 周 (如 */15 * * * *)"
                      value={cronExpr}
                      onChange={(e) => setCronExpr(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
                    />

                    {/* Presets */}
                    <div className="flex flex-wrap gap-1.5 text-[10px]">
                      <button
                        type="button"
                        onClick={() => setCronExpr("*/15 * * * *")}
                        className="px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-mono"
                      >
                        每15分钟
                      </button>
                      <button
                        type="button"
                        onClick={() => setCronExpr("0 9-18 * * 1-5")}
                        className="px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-mono"
                      >
                        工作日每小时
                      </button>
                      <button
                        type="button"
                        onClick={() => setCronExpr("0 2 * * *")}
                        className="px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-mono"
                      >
                        每天凌晨2点
                      </button>
                      <button
                        type="button"
                        onClick={() => setCronExpr("0 9 * * 1")}
                        className="px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-mono"
                      >
                        每周一早9点
                      </button>
                    </div>

                    {/* Validation Feedback */}
                    {cronValidation && (
                      <div className={`p-2.5 rounded-md text-xs border ${
                        cronValidation.valid
                          ? "bg-emerald-950/40 border-emerald-800/50 text-emerald-300"
                          : "bg-rose-950/40 border-rose-800/50 text-rose-300"
                      }`}>
                        {cronValidation.valid ? (
                          <div>
                            <div className="font-semibold flex items-center gap-1.5">
                              <CheckCircle2 size={13} />
                              <span>{cronValidation.description}</span>
                            </div>
                            {cronValidation.next_runs && cronValidation.next_runs.length > 0 && (
                              <div className="text-[10px] text-emerald-400/80 font-mono mt-1">
                                下次预估: {cronValidation.next_runs[0]}
                              </div>
                            )}
                          </div>
                        ) : (
                          <div className="flex items-center gap-1.5">
                            <AlertCircle size={13} />
                            <span>{cronValidation.error}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                <div className="pt-3 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setIsCreateOpen(false)}
                    className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded text-xs"
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 bg-zinc-100 text-zinc-900 hover:bg-white font-semibold rounded text-xs shadow-xs"
                  >
                    创建监控计划
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

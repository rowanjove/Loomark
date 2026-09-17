import React, { useState, useEffect, useRef } from "react";
import { CrawlJob, JobStats, CrawlLog } from "../../types";
import { api, subscribeToCrawlJob } from "../../services/api";
import {
  Activity, Play, Pause, Square, RotateCcw,
  CheckCircle2, AlertTriangle, Clock, Gauge, Terminal, ArrowLeft
} from "lucide-react";

interface CrawlMonitorProps {
  jobId: string;
  onBack?: () => void;
  onViewDocuments?: (projectId: string) => void;
}

export const CrawlMonitor: React.FC<CrawlMonitorProps> = ({ jobId, onBack, onViewDocuments }) => {
  const [job, setJob] = useState<CrawlJob | null>(null);
  const [stats, setStats] = useState<JobStats>({
    discovered: 0,
    queued: 0,
    fetching: 0,
    fetched: 0,
    parsed: 0,
    failed: 0,
    skipped: 0,
    pages_per_second: 0.0
  });
  const [logs, setLogs] = useState<CrawlLog[]>([]);
  const [logFilter, setLogFilter] = useState<string>("ALL");
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Load job details & initial logs
  const fetchJobInfo = async () => {
    try {
      const data = await api.getCrawlJob(jobId);
      setJob(data);
      if (data.stats_json) {
        try {
          const parsedStats = JSON.parse(data.stats_json);
          setStats((prev) => ({ ...prev, ...parsedStats }));
        } catch {}
      }
      const initialLogs = await api.getCrawlLogs(jobId, 200);
      setLogs(initialLogs.map((l) => ({ level: l.level as any, message: l.message, timestamp: l.timestamp })));
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchJobInfo();

    // Subscribe to real-time WebSocket updates
    const unsubscribe = subscribeToCrawlJob(
      jobId,
      (newStats) => {
        setStats((prev) => ({ ...prev, ...newStats }));
      },
      (newLog) => {
        setLogs((prev) => [...prev.slice(-400), newLog]);
      }
    );

    const pollTimer = setInterval(fetchJobInfo, 3000);

    return () => {
      unsubscribe();
      clearInterval(pollTimer);
    };
  }, [jobId]);

  // Auto-scroll logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const handlePause = async () => {
    await api.pauseCrawlJob(jobId);
    fetchJobInfo();
  };

  const handleResume = async () => {
    await api.resumeCrawlJob(jobId);
    fetchJobInfo();
  };

  const handleStop = async () => {
    if (confirm("确定要停止当前的采集任务吗？")) {
      await api.stopCrawlJob(jobId);
      fetchJobInfo();
    }
  };

  const handleRetry = async () => {
    const res = await api.retryCrawlJob(jobId);
    alert(`已将 ${res.retried_count} 个失败的 URL 重新加入采集队列`);
    fetchJobInfo();
  };

  const filteredLogs = logs.filter((l) => {
    if (logFilter === "ALL") return true;
    return l.level === logFilter;
  });

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-zinc-950">
      {/* Top Bar */}
      <div className="h-14 border-b border-zinc-800/80 px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          {onBack && (
            <button onClick={onBack} className="p-1.5 text-zinc-400 hover:text-zinc-100 rounded-md hover:bg-zinc-800 transition-colors">
              <ArrowLeft size={16} />
            </button>
          )}
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-zinc-100">{job?.name || "采集任务监控"}</span>
              <span className={`text-[10px] font-mono font-medium px-2 py-0.5 rounded-full ${
                job?.status === "RUNNING" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                job?.status === "PAUSED" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                job?.status === "COMPLETED" ? "bg-sky-500/10 text-sky-400 border border-sky-500/20" :
                "bg-zinc-800 text-zinc-400"
              }`}>
                {job?.status || "LOADING"}
              </span>
            </div>
            <p className="text-[11px] text-zinc-400 font-mono">Job ID: {jobId.slice(0, 8)}</p>
          </div>
        </div>

        {/* Task Control Actions */}
        <div className="flex items-center gap-2">
          {job?.status === "RUNNING" && (
            <button
              onClick={handlePause}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-md transition-colors"
            >
              <Pause size={13} />
              <span>暂停</span>
            </button>
          )}

          {job?.status === "PAUSED" && (
            <button
              onClick={handleResume}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-md transition-colors"
            >
              <Play size={13} className="fill-white stroke-none" />
              <span>继续</span>
            </button>
          )}

          {job?.status !== "COMPLETED" && job?.status !== "STOPPED" && (
            <button
              onClick={handleStop}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/40 text-rose-300 text-xs font-medium rounded-md transition-colors"
            >
              <Square size={12} className="fill-rose-300 stroke-none" />
              <span>停止</span>
            </button>
          )}

          {stats.failed > 0 && (
            <button
              onClick={handleRetry}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-md transition-colors"
            >
              <RotateCcw size={13} />
              <span>重试失败项 ({stats.failed})</span>
            </button>
          )}

          {onViewDocuments && job?.project_id && (
            <button
              onClick={() => onViewDocuments(job.project_id)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-100 text-zinc-900 hover:bg-white text-xs font-semibold rounded-md transition-colors ml-2"
            >
              <span>查看归档文档 ({stats.parsed})</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Monitoring Content */}
      <div className="flex-1 flex flex-col overflow-hidden p-6 gap-5">
        {/* Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 shrink-0">
          <div className="bg-zinc-900/80 border border-zinc-800/80 p-3.5 rounded-lg">
            <div className="text-[11px] text-zinc-400 mb-1 flex items-center justify-between">
              <span>已完成归档</span>
              <CheckCircle2 size={13} className="text-emerald-400" />
            </div>
            <div className="text-xl font-semibold font-mono text-zinc-100">{stats.parsed}</div>
          </div>

          <div className="bg-zinc-900/80 border border-zinc-800/80 p-3.5 rounded-lg">
            <div className="text-[11px] text-zinc-400 mb-1 flex items-center justify-between">
              <span>采集中 (并发)</span>
              <Activity size={13} className="text-amber-400 animate-spin" />
            </div>
            <div className="text-xl font-semibold font-mono text-amber-400">{stats.fetching}</div>
          </div>

          <div className="bg-zinc-900/80 border border-zinc-800/80 p-3.5 rounded-lg">
            <div className="text-[11px] text-zinc-400 mb-1 flex items-center justify-between">
              <span>等待队列</span>
              <Clock size={13} className="text-sky-400" />
            </div>
            <div className="text-xl font-semibold font-mono text-zinc-200">{stats.queued}</div>
          </div>

          <div className="bg-zinc-900/80 border border-zinc-800/80 p-3.5 rounded-lg">
            <div className="text-[11px] text-zinc-400 mb-1 flex items-center justify-between">
              <span>已发现总 URL</span>
              <span className="text-zinc-500 font-mono">Frontier</span>
            </div>
            <div className="text-xl font-semibold font-mono text-zinc-300">
              {stats.parsed + stats.queued + stats.fetching + stats.failed + stats.skipped}
            </div>
          </div>

          <div className="bg-zinc-900/80 border border-zinc-800/80 p-3.5 rounded-lg">
            <div className="text-[11px] text-zinc-400 mb-1 flex items-center justify-between">
              <span>失败异常</span>
              <AlertTriangle size={13} className="text-rose-400" />
            </div>
            <div className={`text-xl font-semibold font-mono ${stats.failed > 0 ? "text-rose-400" : "text-zinc-400"}`}>
              {stats.failed}
            </div>
          </div>

          <div className="bg-zinc-900/80 border border-zinc-800/80 p-3.5 rounded-lg">
            <div className="text-[11px] text-zinc-400 mb-1 flex items-center justify-between">
              <span>瞬时速率</span>
              <Gauge size={13} className="text-purple-400" />
            </div>
            <div className="text-xl font-semibold font-mono text-purple-300">
              {stats.pages_per_second || 0} <span className="text-xs font-normal text-zinc-500">p/s</span>
            </div>
          </div>
        </div>

        {/* Real-time Streaming Logs Terminal */}
        <div className="flex-1 bg-zinc-950 border border-zinc-800/90 rounded-lg flex flex-col overflow-hidden shadow-inner font-mono">
          {/* Terminal Header */}
          <div className="h-9 px-4 bg-zinc-900/90 border-b border-zinc-800 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2 text-xs text-zinc-300">
              <Terminal size={14} className="text-zinc-400" />
              <span>实时抓取事件流 (Event Stream)</span>
            </div>

            <div className="flex items-center gap-1.5 text-[11px]">
              {["ALL", "INFO", "WARNING", "ERROR"].map((lvl) => (
                <button
                  key={lvl}
                  onClick={() => setLogFilter(lvl)}
                  className={`px-2 py-0.5 rounded transition-colors ${
                    logFilter === lvl
                      ? "bg-zinc-800 text-zinc-100 font-semibold"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  {lvl}
                </button>
              ))}
              <button
                onClick={() => setLogs([])}
                className="text-zinc-500 hover:text-zinc-300 px-2 py-0.5 ml-2"
              >
                清空
              </button>
            </div>
          </div>

          {/* Terminal Body */}
          <div
            ref={logContainerRef}
            className="flex-1 p-4 overflow-y-auto space-y-1 text-xs select-text"
          >
            {filteredLogs.length === 0 ? (
              <div className="h-full flex items-center justify-center text-zinc-600 text-xs">
                等待抓取事件输出...
              </div>
            ) : (
              filteredLogs.map((log, index) => (
                <div key={index} className="flex items-start gap-2.5 leading-relaxed hover:bg-zinc-900/40 px-1.5 py-0.5 rounded">
                  <span className="text-zinc-600 shrink-0">{log.timestamp || "00:00:00"}</span>
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-semibold shrink-0 ${
                    log.level === "INFO" ? "bg-emerald-500/10 text-emerald-400" :
                    log.level === "WARNING" ? "bg-amber-500/10 text-amber-400" :
                    log.level === "ERROR" ? "bg-rose-500/10 text-rose-400" :
                    "bg-zinc-800 text-zinc-400"
                  }`}>
                    {log.level}
                  </span>
                  <span className="text-zinc-300 break-all">{log.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

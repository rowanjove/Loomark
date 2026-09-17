import React from "react";
import { Server, Globe, Cpu, Database } from "lucide-react";

interface StatusBarProps {
  engineOnline: boolean;
  activeJobsCount: number;
}

export const StatusBar: React.FC<StatusBarProps> = ({ engineOnline, activeJobsCount }) => {
  return (
    <footer className="h-7 bg-zinc-950 border-t border-zinc-800/80 px-3 flex items-center justify-between text-[11px] text-zinc-400 select-none shrink-0 font-mono">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <Server size={12} className={engineOnline ? "text-emerald-400" : "text-rose-400"} />
          <span className="text-zinc-300">Engine:</span>
          <span className={engineOnline ? "text-emerald-400" : "text-rose-400"}>
            {engineOnline ? "Ready" : "Offline"}
          </span>
        </div>

        <div className="flex items-center gap-1.5 text-emerald-400">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>127.0.0.1:8765</span>
        </div>

        <div className="flex items-center gap-1.5">
          <Globe size={12} className="text-sky-400" />
          <span className="text-zinc-300">Browser:</span>
          <span className="text-zinc-400">Playwright Smart</span>
        </div>

        <div className="flex items-center gap-1.5">
          <Cpu size={12} className="text-purple-400" />
          <span className="text-zinc-300">AI Pipeline:</span>
          <span className="text-zinc-400">Decoupled Queue</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {activeJobsCount > 0 && (
          <div className="flex items-center gap-1 text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>{activeJobsCount} 采集中</span>
          </div>
        )}
        <div className="flex items-center gap-1.5">
          <Database size={12} className="text-zinc-400" />
          <span>FTS5 Indexed</span>
        </div>
      </div>
    </footer>
  );
};

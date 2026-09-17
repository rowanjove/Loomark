import React from "react";
import { FolderKanban, Activity, FileText, Settings, Boxes, Plus, Eye, Compass, BookOpen } from "lucide-react";

export type NavTab = "projects" | "crawls" | "documents" | "monitoring" | "plugins" | "research" | "settings";

interface SidebarProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  onNewProject: () => void;
  onOpenGuide: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange, onNewProject, onOpenGuide }) => {
  const navItems: { id: NavTab; label: string; icon: React.ReactNode }[] = [
    { id: "projects", label: "项目管理", icon: <FolderKanban size={24} /> },
    { id: "crawls", label: "采集监控", icon: <Activity size={24} /> },
    { id: "documents", label: "文档归档", icon: <FileText size={24} /> },
    { id: "monitoring", label: "网站监控", icon: <Eye size={24} /> },
    { id: "plugins", label: "规则与插件", icon: <Boxes size={24} /> },
    { id: "research", label: "定向调研", icon: <Compass size={24} /> },
  ];

  return (
    <aside className="w-64 bg-zinc-950 border-r border-zinc-800/80 flex flex-col justify-between shrink-0 select-none">
      <div>
        {/* Brand & App Icon */}
        <div className="h-14 px-4 border-b border-zinc-800/60 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <img
              src="/app-icon.png"
              alt="Loomark"
              className="w-7 h-7 rounded-md object-contain ring-1 ring-zinc-700/50 shadow-sm"
              onError={(e) => {
                // Fallback if image fails to load
                (e.target as HTMLElement).style.display = 'none';
              }}
            />
            <div className="flex flex-col">
              <span className="font-semibold text-sm tracking-tight text-zinc-100">
                Loomark
              </span>
              <span className="text-[11px] text-zinc-400 font-normal">Web Content Intelligence</span>
            </div>
          </div>
        </div>

        {/* Action Button (放大 0.5 倍) */}
        <div className="p-3">
          <button
            onClick={onNewProject}
            className="w-full flex items-center justify-center gap-2.5 py-3 px-4 rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white text-[15px] font-semibold shadow-sm transition-all active:scale-[0.98]"
          >
            <Plus size={20} className="stroke-[2.5]" />
            <span>新建采集项目</span>
          </button>
        </div>

        {/* Navigation List (按钮整体放大 0.5 倍) */}
        <nav className="px-3 space-y-1.5 mt-1">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-lg text-[15px] font-medium transition-colors ${
                  isActive
                    ? "bg-zinc-800/90 text-zinc-100 font-semibold shadow-sm"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60"
                }`}
              >
                <span className={isActive ? "text-zinc-100" : "text-zinc-400"}>
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* 底部左下角：放置使用教程与系统设置 */}
      <div className="p-3 border-t border-zinc-800/60 space-y-1.5">
        <button
          onClick={onOpenGuide}
          className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg bg-zinc-900/90 hover:bg-zinc-800 text-zinc-200 border border-emerald-500/30 text-[14px] font-medium transition-all group shadow-sm hover:border-emerald-500/60"
        >
          <div className="flex items-center gap-3">
            <BookOpen size={20} className="text-emerald-400 group-hover:scale-110 transition-transform" />
            <span className="font-semibold text-zinc-100">使用教程</span>
          </div>
          <span className="px-2 py-0.5 text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 rounded-full">
            新手指南
          </span>
        </button>

        <button
          onClick={() => onTabChange("settings")}
          className={`w-full flex items-center gap-3.5 px-4 py-2.5 rounded-lg text-[14px] font-medium transition-colors ${
            activeTab === "settings"
              ? "bg-zinc-800/90 text-zinc-100 font-semibold shadow-sm"
              : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60"
          }`}
        >
          <span className={activeTab === "settings" ? "text-zinc-100" : "text-zinc-400"}>
            <Settings size={20} />
          </span>
          <span>系统设置</span>
        </button>
      </div>
    </aside>
  );
};

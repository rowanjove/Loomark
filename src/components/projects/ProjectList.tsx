import React, { useState } from "react";
import { Project } from "../../types";
import { FolderKanban, Search, Plus, FileText, Globe, ArrowUpRight, Trash2, BookOpen, Zap, Layers } from "lucide-react";

interface ProjectListProps {
  projects: Project[];
  onSelectProject: (project: Project) => void;
  onNewProject: () => void;
  onDeleteProject: (projectId: string) => void;
  onStartCrawl: (project: Project) => void;
  onOpenGuide?: () => void;
}

export const ProjectList: React.FC<ProjectListProps> = ({
  projects,
  onSelectProject,
  onNewProject,
  onDeleteProject,
  onStartCrawl,
  onOpenGuide
}) => {
  const [search, setSearch] = useState("");

  const filtered = projects.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    (p.description && p.description.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-zinc-950">
      {/* Header Bar */}
      <div className="h-14 border-b border-zinc-800/80 px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
            <FolderKanban size={18} className="text-zinc-400" />
            <span>研究与采集项目</span>
          </h1>
          <span className="text-xs text-zinc-400 font-mono px-2 py-0.5 bg-zinc-900 border border-zinc-800 rounded-full">
            {projects.length} 个项目
          </span>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative w-64">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-400" />
            <input
              type="text"
              placeholder="搜索项目..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-md pl-8 pr-3 py-1.5 text-xs text-zinc-200 placeholder:text-zinc-400 focus:outline-none focus:border-zinc-600 transition-colors"
            />
          </div>

          <div className="flex items-center gap-2">
            {onOpenGuide && (
              <button
                onClick={onOpenGuide}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-700/80 hover:border-emerald-500/50 text-xs font-semibold rounded-md shadow-xs transition-all"
              >
                <BookOpen size={14} className="text-emerald-400" />
                <span>使用教程</span>
              </button>
            )}

            <button
              onClick={onNewProject}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-100 text-zinc-900 hover:bg-white text-xs font-semibold rounded-md shadow-xs transition-all active:scale-95"
            >
              <Plus size={14} className="stroke-[2.5]" />
              <span>新建项目</span>
            </button>
          </div>
        </div>
      </div>

      {/* Projects Grid */}
      <div className="flex-1 overflow-y-auto p-6">
        {filtered.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 text-zinc-400 max-w-lg mx-auto">
            <div className="w-14 h-14 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-4 text-zinc-300 shadow-md">
              <FolderKanban size={28} />
            </div>
            <h3 className="text-base font-semibold text-zinc-200">欢迎使用 Loomark 网页采集与智能分析</h3>
            <p className="text-xs text-zinc-400 mt-2 mb-5 leading-relaxed">
              底层具备极速本地纯规则爬虫能力（无需任何 AI），亦可按需开启 AI 智能摘要。请先创建一个研究项目开始使用。
            </p>

            {/* Quick 3-step hint card */}
            <div className="w-full p-4 bg-zinc-900/60 border border-zinc-800/80 rounded-xl text-left text-xs mb-6 space-y-2">
              <div className="font-semibold text-zinc-300 flex items-center gap-1.5 text-[11px] uppercase tracking-wider">
                <Layers size={13} className="text-emerald-400" />
                <span>新手 3 步极速上手：</span>
              </div>
              <div className="text-[11px] text-zinc-400 space-y-1">
                <div>1. 点击【立即创建新项目】输入项目名称</div>
                <div>2. 点击【发起新采集】输入网址（可选纯规则抓取或 AI 增强）</div>
                <div>3. 采集完成后在【文档归档】中查阅纯净 Markdown 并一键导出</div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {onOpenGuide && (
                <button
                  onClick={onOpenGuide}
                  className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-700 text-xs font-semibold rounded-md shadow-xs flex items-center gap-1.5 transition-colors"
                >
                  <BookOpen size={14} className="text-emerald-400" />
                  <span>查看完整使用教程</span>
                </button>
              )}
              <button
                onClick={onNewProject}
                className="px-4 py-2 bg-zinc-100 text-zinc-900 hover:bg-white text-xs font-semibold rounded-md shadow-xs flex items-center gap-1.5 transition-all"
              >
                <Plus size={14} className="stroke-[2.5]" />
                <span>立即创建新项目</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((project) => (
              <div
                key={project.id}
                onClick={() => onSelectProject(project)}
                className="group relative bg-zinc-900/60 hover:bg-zinc-900 border border-zinc-800/80 hover:border-zinc-700/80 rounded-lg p-5 transition-all cursor-pointer flex flex-col justify-between shadow-xs hover:shadow-md"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <h3 className="text-sm font-semibold text-zinc-100 group-hover:text-white transition-colors line-clamp-1">
                      {project.name}
                    </h3>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                      <button
                        title="删除项目"
                        onClick={() => {
                          if (confirm(`确定要删除项目 "${project.name}" 及其所有采集数据吗？`)) {
                            onDeleteProject(project.id);
                          }
                        }}
                        className="p-1 text-zinc-400 hover:text-rose-400 rounded transition-colors"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>

                  <p className="text-xs text-zinc-400 line-clamp-2 mb-4 leading-relaxed">
                    {project.description || "暂无项目描述"}
                  </p>
                </div>

                <div>
                  <div className="grid grid-cols-2 gap-2 pt-3 border-t border-zinc-800/60 text-[11px] text-zinc-400">
                    <div className="flex items-center gap-1.5">
                      <FileText size={13} className="text-zinc-400" />
                      <span>{project.document_count} 篇文档</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Globe size={13} className="text-zinc-400" />
                      <span>{project.target_count} 个采集源</span>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-zinc-800/40 flex items-center justify-between text-[11px]">
                    <span className="text-zinc-400 font-mono">
                      更新于 {project.updated_at.slice(0, 10)}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onStartCrawl(project);
                      }}
                      className="flex items-center gap-1 text-xs text-zinc-200 hover:text-white font-medium bg-zinc-800 hover:bg-zinc-700 px-2.5 py-1 rounded transition-colors"
                    >
                      <span>发起采集</span>
                      <ArrowUpRight size={13} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

import React, { useState, useEffect } from "react";
import { DocumentItem } from "../../types";
import { api } from "../../services/api";
import {
  Search, Filter, FileText, Globe, Calendar,
  Download, RefreshCw, CheckSquare, Square
} from "lucide-react";

interface DocumentTableProps {
  projectId: string;
  onSelectDocument: (doc: DocumentItem) => void;
  onOpenExport: (selectedDocIds?: string[]) => void;
}

export const DocumentTable: React.FC<DocumentTableProps> = ({
  projectId,
  onSelectDocument,
  onOpenExport
}) => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [total, setTotal] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [searchMode, setSearchMode] = useState<"hybrid" | "fts" | "semantic">("hybrid");
  const [domainFilter, setDomainFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(0);
  const pageSize = 25;

  // 300ms Debounce for search
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const res = await api.getDocuments({
        projectId,
        search: search.trim() || undefined,
        searchMode: search.trim() ? searchMode : undefined,
        domain: domainFilter || undefined,
        docType: typeFilter || undefined,
        limit: pageSize,
        offset: page * pageSize
      });
      setDocuments(res.items);
      setTotal(res.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [projectId, search, searchMode, domainFilter, typeFilter, page]);

  const toggleSelectAll = () => {
    if (selectedIds.size === documents.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(documents.map((d) => d.id)));
    }
  };

  const toggleSelect = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-zinc-950">
      {/* Top Filter Bar */}
      <div className="h-14 border-b border-zinc-800/80 px-6 flex items-center justify-between shrink-0 gap-4">
        {/* Left: Search Bar & Mode Selector */}
        <div className="flex items-center gap-2.5 flex-1 max-w-lg">
          <div className="relative w-full">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
            <input
              type="text"
              placeholder={
                searchMode === "hybrid"
                  ? "智能混合检索 (关键词 + 向量语义概念)..."
                  : searchMode === "semantic"
                  ? "概念语义检索 (相似意图与语义关联)..."
                  : "FTS5 关键词全文检索 (精准词法匹配)..."
              }
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-md pl-9 pr-3 py-1.5 text-xs text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-500"
            />
          </div>

          <div className="flex items-center bg-zinc-900 border border-zinc-800 rounded-md p-0.5 shrink-0 text-[11px]">
            <button
              type="button"
              onClick={() => { setSearchMode("hybrid"); setPage(0); }}
              className={`px-2 py-1 rounded transition-colors ${
                searchMode === "hybrid" ? "bg-zinc-800 text-zinc-100 font-medium" : "text-zinc-400 hover:text-zinc-200"
              }`}
              title="Reciprocal Rank Fusion 混合排序"
            >
              混合
            </button>
            <button
              type="button"
              onClick={() => { setSearchMode("semantic"); setPage(0); }}
              className={`px-2 py-1 rounded transition-colors ${
                searchMode === "semantic" ? "bg-zinc-800 text-zinc-100 font-medium" : "text-zinc-400 hover:text-zinc-200"
              }`}
              title="纯向量余弦相似度检索"
            >
              语义
            </button>
            <button
              type="button"
              onClick={() => { setSearchMode("fts"); setPage(0); }}
              className={`px-2 py-1 rounded transition-colors ${
                searchMode === "fts" ? "bg-zinc-800 text-zinc-100 font-medium" : "text-zinc-400 hover:text-zinc-200"
              }`}
              title="SQLite FTS5 关键词全文检索"
            >
              FTS5
            </button>
          </div>
        </div>


        {/* Right: Actions & Filters */}
        <div className="flex items-center gap-2.5">
          <select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setPage(0);
            }}
            className="bg-zinc-900 border border-zinc-800 rounded-md px-2.5 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-zinc-500"
          >
            <option value="">全部类型</option>
            <option value="article">文章 (Article)</option>
            <option value="website">网页 (Website)</option>
            <option value="video">视频/字幕 (Video)</option>
          </select>

          <button
            onClick={() => fetchDocs()}
            title="刷新文档"
            className="p-1.5 text-zinc-400 hover:text-zinc-200 bg-zinc-900 border border-zinc-800 rounded-md hover:bg-zinc-800 transition-colors"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>

          <button
            onClick={() => onOpenExport(selectedIds.size > 0 ? Array.from(selectedIds) : undefined)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-100 text-zinc-900 hover:bg-white text-xs font-semibold rounded-md transition-all shadow-xs"
          >
            <Download size={13} />
            <span>导出数据 {selectedIds.size > 0 ? `(${selectedIds.size})` : `(全量 ${total})`}</span>
          </button>
        </div>
      </div>

      {/* Table Content */}
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-left border-collapse">
          <thead className="bg-zinc-900/90 text-zinc-400 text-[11px] font-medium sticky top-0 border-b border-zinc-800 z-10 select-none">
            <tr>
              <th className="w-10 px-4 py-2.5">
                <button onClick={toggleSelectAll} className="text-zinc-400 hover:text-zinc-200">
                  {selectedIds.size > 0 && selectedIds.size === documents.length ? (
                    <CheckSquare size={14} className="text-zinc-100" />
                  ) : (
                    <Square size={14} />
                  )}
                </button>
              </th>
              <th className="px-3 py-2.5">标题与链接</th>
              <th className="px-3 py-2.5 w-36">域名</th>
              <th className="px-3 py-2.5 w-24">类型</th>
              <th className="px-3 py-2.5 w-28">状态</th>
              <th className="px-4 py-2.5 w-32 text-right">采集时间</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/50 text-xs">
            {documents.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-16 text-zinc-500">
                  {loading ? "检索中..." : "没有找到匹配的归档文档"}
                </td>
              </tr>
            ) : (
              documents.map((doc) => {
                const isSelected = selectedIds.has(doc.id);
                return (
                  <tr
                    key={doc.id}
                    onClick={() => onSelectDocument(doc)}
                    className={`hover:bg-zinc-900/70 transition-colors cursor-pointer ${
                      isSelected ? "bg-zinc-900/50" : ""
                    }`}
                  >
                    <td className="px-4 py-3" onClick={(e) => toggleSelect(doc.id, e)}>
                      <button className="text-zinc-400 hover:text-zinc-200">
                        {isSelected ? (
                          <CheckSquare size={14} className="text-zinc-100" />
                        ) : (
                          <Square size={14} />
                        )}
                      </button>
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-zinc-100 line-clamp-1 hover:text-white">
                          {doc.title || "Untitled Document"}
                        </span>
                        {doc.search_score !== undefined && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-950/80 text-blue-400 border border-blue-800/40 shrink-0">
                            得分 {doc.search_score}
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-zinc-500 font-mono line-clamp-1 mt-0.5">
                        {doc.url}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-zinc-400 font-mono text-[11px]">
                      {doc.domain}
                    </td>
                    <td className="px-3 py-3">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800/80 text-zinc-300">
                        {doc.type}
                      </span>
                    </td>
                    <td className="px-3 py-3">
                      <span className={`text-[10px] font-mono font-medium px-2 py-0.5 rounded ${
                        doc.change_status === "NEW" ? "bg-emerald-500/10 text-emerald-400" :
                        doc.change_status === "UPDATED" ? "bg-amber-500/10 text-amber-400" :
                        "bg-zinc-800 text-zinc-400"
                      }`}>
                        {doc.change_status || "NEW"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-zinc-500 font-mono text-[11px]">
                      {doc.created_at ? doc.created_at.slice(0, 16).replace("T", " ") : "-"}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="h-11 border-t border-zinc-800 px-6 flex items-center justify-between text-xs text-zinc-400 shrink-0 select-none">
        <span>共 {total} 篇文档</span>
        <div className="flex items-center gap-2">
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            className="px-2.5 py-1 bg-zinc-900 border border-zinc-800 rounded hover:bg-zinc-800 text-zinc-300 disabled:opacity-30"
          >
            上一页
          </button>
          <span className="font-mono text-zinc-300">
            {page + 1} / {Math.max(1, Math.ceil(total / pageSize))}
          </span>
          <button
            disabled={(page + 1) * pageSize >= total}
            onClick={() => setPage((p) => p + 1)}
            className="px-2.5 py-1 bg-zinc-900 border border-zinc-800 rounded hover:bg-zinc-800 text-zinc-300 disabled:opacity-30"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  );
};

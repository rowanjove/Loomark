import React, { useState } from "react";
import { api } from "../../services/api";
import { X, Download, FileText, CheckCircle2 } from "lucide-react";

interface ExportModalProps {
  projectId: string;
  docIds?: string[];
  isOpen: boolean;
  onClose: () => void;
}

export const ExportModal: React.FC<ExportModalProps> = ({ projectId, docIds, isOpen, onClose }) => {
  const [format, setFormat] = useState<"markdown" | "json" | "jsonl" | "csv" | "xlsx" | "parquet" | "html" | "txt">("markdown");
  const [loading, setLoading] = useState(false);
  const [resultPath, setResultPath] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleExport = async () => {
    setLoading(true);
    setResultPath(null);
    try {
      const res = await api.exportProject(projectId, format, docIds);
      setResultPath(res.export_path);
    } catch (e: any) {
      alert(`导出失败: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="px-5 py-4 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2 text-zinc-100 font-semibold text-sm">
            <Download size={18} className="text-zinc-400" />
            <span>导出采集归档数据</span>
          </div>
          <button onClick={onClose} className="p-1 text-zinc-400 hover:text-zinc-200 rounded">
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div className="text-xs text-zinc-400">
            {docIds && docIds.length > 0 ? (
              <span>已选择 <strong className="text-zinc-200">{docIds.length}</strong> 篇文档导出</span>
            ) : (
              <span>导出当前项目全量已归档文档</span>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-2">选择导出数据格式</label>
            <div className="grid grid-cols-2 gap-2 text-xs max-h-64 overflow-y-auto pr-1">
              {[
                { id: "markdown", label: "Markdown 文件夹", desc: "带 YAML Frontmatter" },
                { id: "xlsx", label: "Excel 工作簿 (.xlsx)", desc: "概览 + 明细多工作表" },
                { id: "html", label: "独立 HTML 离线报告", desc: "自包含排版与左侧目录" },
                { id: "json", label: "JSON 数据集", desc: "标准格式数组" },
                { id: "jsonl", label: "JSONL 数据流", desc: "逐行 JSON 适合大模型" },
                { id: "csv", label: "CSV 表格", desc: "通用逗号分隔符" },
                { id: "txt", label: "纯文本合集 (.txt)", desc: "结构化整编纯文本" },
                { id: "parquet", label: "Parquet 列式存储", desc: "适合大数据 / DuckDB" },
              ].map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setFormat(item.id as any)}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    format === item.id
                      ? "bg-zinc-800 border-zinc-500 text-zinc-100 shadow-xs"
                      : "bg-zinc-950 border-zinc-800 text-zinc-400 hover:bg-zinc-900"
                  }`}
                >
                  <div className="font-semibold">{item.label}</div>
                  <div className="text-[10px] text-zinc-500 mt-0.5">{item.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {resultPath && (
            <div className="p-3 bg-emerald-950/30 border border-emerald-800/60 rounded-lg text-xs space-y-1.5 animate-in fade-in">
              <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                <CheckCircle2 size={14} />
                <span>导出成功！</span>
              </div>
              <div className="text-[11px] text-zinc-300 font-mono break-all bg-zinc-950 p-2 rounded">
                {resultPath}
              </div>
            </div>
          )}

          <div className="pt-2 flex items-center justify-end gap-2.5">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-md"
            >
              关闭
            </button>
            <button
              onClick={handleExport}
              disabled={loading}
              className="px-4 py-1.5 bg-zinc-100 text-zinc-900 hover:bg-white text-xs font-semibold rounded-md shadow-xs transition-all disabled:opacity-50"
            >
              {loading ? "导出中..." : "确认并导出"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

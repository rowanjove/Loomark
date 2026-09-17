import React, { useState, useEffect } from "react";
import { DocumentItem, SnapshotHistoryItem, AIArtifact, DiffResult, SubtitleItem, SubtitleSegment, DocumentChunk } from "../../types";
import { api } from "../../services/api";
import {
  X, ExternalLink, Sparkles, Code2, History,
  FileText, AlignLeft, Info, Calendar, User, Clock, Film, Copy, Check, Layers
} from "lucide-react";

interface DocumentViewerProps {
  document: DocumentItem;
  onClose: () => void;
}

type TabType = "clean" | "markdown" | "raw" | "ai" | "diff" | "subtitles" | "chunks" | "metadata";

export const DocumentViewer: React.FC<DocumentViewerProps> = ({ document: initialDoc, onClose }) => {
  const [doc, setDoc] = useState<DocumentItem>(initialDoc);
  const [activeTab, setActiveTab] = useState<TabType>("clean");
  const [history, setHistory] = useState<SnapshotHistoryItem[]>([]);
  const [aiArtifacts, setAiArtifacts] = useState<AIArtifact[]>([]);
  const [subtitles, setSubtitles] = useState<SubtitleItem[]>([]);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);
  const [generatingAi, setGeneratingAi] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [copiedSub, setCopiedSub] = useState(false);

  useEffect(() => {
    // Load snapshot history, AI artifacts, subtitles, chunks and diff
    api.getDocumentHistory(doc.id).then(setHistory);
    api.getDocumentAIArtifacts(doc.id).then(setAiArtifacts);
    api.getDocumentSubtitles(doc.id).then(setSubtitles);
    api.getDocumentChunks(doc.id).then(setChunks);
    api.getDocumentDiff(doc.id).then(setDiffResult);
  }, [doc.id]);

  const handleTriggerAI = async () => {
    setGeneratingAi(true);
    setAiError(null);
    try {
      const art = await api.triggerDocumentAI(doc.id, "article_summary_v1");
      setAiArtifacts((prev) => [art, ...prev]);
    } catch (e: any) {
      setAiError(e.message || "生成 AI 摘要失败");
    } finally {
      setGeneratingAi(false);
    }
  };

  const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
    { id: "clean", label: "清洗排版", icon: <AlignLeft size={14} /> },
    { id: "markdown", label: "Markdown", icon: <FileText size={14} /> },
    { id: "chunks", label: `段落分块 (${chunks.length})`, icon: <Layers size={14} className="text-cyan-400" /> },
    { id: "ai", label: "AI 研报与摘要", icon: <Sparkles size={14} className="text-purple-400" /> },
    { id: "raw", label: "Raw HTML", icon: <Code2 size={14} /> },
    { id: "diff", label: "快照比对", icon: <History size={14} /> },
  ];

  if (doc.type === "video" || subtitles.length > 0) {
    tabs.splice(3, 0, { id: "subtitles", label: `字幕切片 (${subtitles.length})`, icon: <Film size={14} className="text-amber-400" /> });
  }

  tabs.push({ id: "metadata", label: "元数据", icon: <Info size={14} /> });


  // Format seconds to mm:ss
  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const handleCopyAllSubtitles = (segments: SubtitleSegment[]) => {
    const text = segments.map((s) => `[${formatTime(s.start)}] ${s.text}`).join("\n");
    navigator.clipboard.writeText(text);
    setCopiedSub(true);
    setTimeout(() => setCopiedSub(false), 2500);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-5xl h-[88vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Top Header */}
        <div className="h-14 px-6 border-b border-zinc-800 flex items-center justify-between shrink-0 bg-zinc-900">
          <div className="flex items-center gap-3 overflow-hidden mr-4">
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 shrink-0">
              {doc.type}
            </span>
            <h2 className="text-sm font-semibold text-zinc-100 truncate" title={doc.title}>
              {doc.title || "Untitled Document"}
            </h2>
            <a
              href={doc.url}
              target="_blank"
              rel="noreferrer"
              className="text-zinc-500 hover:text-zinc-300 p-1 shrink-0"
              title="在浏览器中打开原网页"
            >
              <ExternalLink size={13} />
            </a>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* Tab Pills */}
            <div className="flex items-center gap-1 bg-zinc-950 p-1 rounded-lg border border-zinc-800">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-xs transition-colors ${
                    activeTab === tab.id
                      ? "bg-zinc-800 text-zinc-100 font-medium shadow-xs"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  {tab.icon}
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>

            <button
              onClick={onClose}
              className="p-1.5 text-zinc-400 hover:text-zinc-200 rounded-md hover:bg-zinc-800 ml-2"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Document Body Area */}
        <div className="flex-1 overflow-y-auto p-8 bg-zinc-950/60 select-text">
          {/* 1. Clean Reader View */}
          {activeTab === "clean" && (
            <article className="max-w-3xl mx-auto space-y-6">
              <header className="border-b border-zinc-800 pb-5">
                <h1 className="text-2xl font-bold text-zinc-100 leading-tight">
                  {doc.title || "Untitled Document"}
                </h1>
                <div className="flex items-center gap-4 text-xs text-zinc-400 mt-3 font-mono">
                  {doc.author && (
                    <span className="flex items-center gap-1">
                      <User size={13} /> {doc.author}
                    </span>
                  )}
                  {doc.published_at && (
                    <span className="flex items-center gap-1">
                      <Calendar size={13} /> {doc.published_at}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Clock size={13} /> 抓取于 {doc.created_at.slice(0, 10)}
                  </span>
                  <span>字数: {doc.text ? doc.text.length : 0}</span>
                </div>
              </header>

              <div className="text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap font-sans space-y-4">
                {doc.text || "正文为空"}
              </div>
            </article>
          )}

          {/* 2. Markdown View */}
          {activeTab === "markdown" && (
            <div className="max-w-3xl mx-auto">
              <div className="flex items-center justify-between mb-3 text-xs text-zinc-400">
                <span>标准化 Markdown 结构</span>
                <button
                  onClick={() => navigator.clipboard.writeText(doc.markdown)}
                  className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded transition-colors text-[11px]"
                >
                  复制 Markdown
                </button>
              </div>
              <pre className="p-4 bg-zinc-900/90 border border-zinc-800 rounded-lg text-xs font-mono text-zinc-300 whitespace-pre-wrap overflow-x-auto">
                {doc.markdown || doc.text}
              </pre>
            </div>
          )}

          {/* 3. Subtitles View (PRD Section 31-35) */}
          {activeTab === "subtitles" && (
            <div className="max-w-3xl mx-auto space-y-4">
              {subtitles.length === 0 ? (
                <div className="text-center py-12 text-zinc-500 text-xs">
                  暂无提取到的字幕切片记录。
                </div>
              ) : (
                subtitles.map((subItem) => {
                  let segments: SubtitleSegment[] = [];
                  try {
                    segments = typeof subItem.segments_json === "string" ? JSON.parse(subItem.segments_json) : subItem.segments_json;
                  } catch {}

                  return (
                    <div key={subItem.id} className="p-5 bg-zinc-900 border border-zinc-800 rounded-xl space-y-4">
                      <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                        <div className="flex items-center gap-2">
                          <Film size={16} className="text-amber-400" />
                          <span className="text-xs font-semibold text-zinc-200">
                            语言: {subItem.language} (来源: {subItem.source})
                          </span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
                            共 {segments.length} 片段
                          </span>
                        </div>
                        <button
                          onClick={() => handleCopyAllSubtitles(segments)}
                          className="flex items-center gap-1.5 px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs rounded transition-colors"
                        >
                          {copiedSub ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                          <span>{copiedSub ? "已复制" : "复制全部字幕文案"}</span>
                        </button>
                      </div>

                      {/* Timeline Stream */}
                      <div className="space-y-2 max-h-[55vh] overflow-y-auto pr-2">
                        {segments.map((seg, idx) => (
                          <div
                            key={idx}
                            className="p-2.5 bg-zinc-950/70 border border-zinc-800/60 rounded-lg flex items-start gap-3 hover:border-zinc-700 transition-colors"
                          >
                            <span className="text-[10px] font-mono text-amber-400 bg-amber-950/40 border border-amber-800/40 px-1.5 py-0.5 rounded shrink-0 mt-0.5">
                              {formatTime(seg.start)}
                            </span>
                            <span className="text-xs text-zinc-200 leading-relaxed font-sans select-text">
                              {seg.text}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* Chunks View (PRD Section 45, 52) */}
          {activeTab === "chunks" && (
            <div className="max-w-3xl mx-auto space-y-4">
              <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-lg flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Layers size={18} className="text-cyan-400" />
                  <div>
                    <h3 className="text-xs font-semibold text-zinc-200">超长文档语义分块 (Chunk Pipeline)</h3>
                    <p className="text-[11px] text-zinc-400">将长文按标点与自然段切片入库，支持分层摘要与微结构阅读</p>
                  </div>
                </div>
                <div className="text-xs font-mono text-cyan-400 bg-cyan-950/40 border border-cyan-800/40 px-2.5 py-1 rounded">
                  共 {chunks.length} 个分段
                </div>
              </div>

              {chunks.length === 0 ? (
                <div className="text-center py-12 text-zinc-500 text-xs">
                  当前文档未生成分块或长度无需分块。
                </div>
              ) : (
                <div className="space-y-3">
                  {chunks.map((chunk) => (
                    <div key={chunk.id} className="p-4 bg-zinc-900/60 border border-zinc-800 rounded-lg space-y-2.5">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-cyan-400 font-semibold bg-cyan-950/60 border border-cyan-800/50 px-2 py-0.5 rounded text-[11px]">
                            Chunk #{chunk.chunk_index + 1}
                          </span>
                          <span className="text-zinc-400 text-[11px]">
                            {chunk.char_count} 字符 · 约 {chunk.token_count} Tokens
                          </span>
                        </div>
                        <span className="text-zinc-500 font-mono text-[10px]">
                          {chunk.created_at ? chunk.created_at.slice(0, 19).replace("T", " ") : ""}
                        </span>
                      </div>

                      {chunk.summary && (
                        <div className="p-2.5 bg-zinc-950 border border-zinc-800/80 rounded text-xs text-zinc-300">
                          <span className="font-semibold text-cyan-300 mr-1.5">分段摘要:</span>
                          {chunk.summary}
                        </div>
                      )}

                      <div className="text-xs text-zinc-300 leading-relaxed font-sans whitespace-pre-wrap select-text bg-zinc-950/50 p-3 rounded border border-zinc-900">
                        {chunk.text}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* 4. AI Analysis View */}
          {activeTab === "ai" && (

            <div className="max-w-3xl mx-auto space-y-5">
              <div className="flex items-center justify-between p-4 bg-zinc-900 border border-zinc-800 rounded-lg">
                <div className="flex items-center gap-2.5">
                  <Sparkles size={18} className="text-purple-400" />
                  <div>
                    <h3 className="text-xs font-semibold text-zinc-200">AI 内容研报 & 摘要</h3>
                    <p className="text-[11px] text-zinc-400">基于清洗后正文自动提取核心观点、关键词与分类</p>
                  </div>
                </div>
                <button
                  onClick={handleTriggerAI}
                  disabled={generatingAi}
                  className="px-3.5 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold rounded-md shadow-xs transition-all flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Sparkles size={13} />
                  <span>{generatingAi ? "生成中..." : "重新生成 AI 摘要"}</span>
                </button>
              </div>

              {aiError && (
                <div className="p-3 bg-rose-950/30 border border-rose-800 text-rose-300 text-xs rounded-lg">
                  {aiError}
                </div>
              )}

              {aiArtifacts.length === 0 ? (
                <div className="text-center py-12 text-zinc-500 text-xs">
                  暂未生成 AI 摘要，点击上方按钮立即生成。
                </div>
              ) : (
                aiArtifacts.map((art) => {
                  const res = typeof art.result_json === "string" ? JSON.parse(art.result_json) : art.result_json;
                  return (
                    <div key={art.id} className="p-5 bg-zinc-900/70 border border-zinc-800 rounded-lg space-y-3">
                      <div className="flex items-center justify-between border-b border-zinc-800/80 pb-2 text-[11px] text-zinc-400">
                        <span className="font-mono text-purple-400 font-medium">{art.model}</span>
                        <span>
                          Tokens: {art.input_tokens + art.output_tokens} (预估费用: ${art.cost.toFixed(4)})
                        </span>
                      </div>
                      <div className="text-xs text-zinc-200 leading-relaxed whitespace-pre-wrap">
                        {res.text || JSON.stringify(res, null, 2)}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* 5. Raw HTML View */}
          {activeTab === "raw" && (
            <div className="max-w-4xl mx-auto space-y-3">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span className="font-mono">本地快照文件: {doc.raw_html_path || "未指定"}</span>
              </div>
              <div className="p-4 bg-zinc-900 border border-zinc-800 rounded-lg text-xs font-mono text-zinc-400 whitespace-pre-wrap overflow-x-auto max-h-[60vh]">
                {doc.raw_html_path ? `原始快照已安全保存至本地：\n${doc.raw_html_path}\n\n用于支持离线算法更新与重新解析。` : "无原始 HTML 快照"}
              </div>
            </div>
          )}

          {/* 6. Visual Diff & Snapshot History View (PRD Section 73) */}
          {activeTab === "diff" && (
            <div className="max-w-3xl mx-auto space-y-6">
              <div className="p-3 bg-zinc-900 border border-zinc-800 rounded-lg text-xs space-y-1">
                <div className="font-semibold text-zinc-200">增量采集状态: {doc.change_status}</div>
                <p className="text-zinc-400">{doc.diff_summary || "本次采集为首次收录。"}</p>
                <div className="text-[11px] font-mono text-zinc-500">
                  Content Hash: {doc.content_hash}
                </div>
              </div>

              {/* Visual Diff Lines Component */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs text-zinc-300 font-semibold">
                  <span>正文版本行级 Diff 对比 (Visual Diff)</span>
                  {diffResult?.has_diff && (
                    <span className="text-[11px] font-mono text-zinc-500">
                      {diffResult.previous_date?.slice(0, 19)} → {diffResult.current_date?.slice(0, 19)}
                    </span>
                  )}
                </div>

                {diffResult?.has_diff ? (
                  <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg max-h-[45vh] overflow-y-auto font-mono text-xs space-y-0.5">
                    {diffResult.diff_lines.map((line, idx) => (
                      <div
                        key={idx}
                        className={`px-2 py-0.5 rounded-xs flex items-start gap-3 ${
                          line.type === "insert"
                            ? "bg-emerald-950/40 text-emerald-300 border-l-2 border-emerald-500"
                            : line.type === "delete"
                            ? "bg-rose-950/40 text-rose-300 border-l-2 border-rose-500 line-through opacity-80"
                            : "text-zinc-400"
                        }`}
                      >
                        <span className="text-zinc-600 select-none w-8 text-right text-[10px]">
                          {line.new_num || line.old_num || "-"}
                        </span>
                        <span className="select-none text-zinc-600 font-bold w-3">
                          {line.type === "insert" ? "+" : line.type === "delete" ? "-" : " "}
                        </span>
                        <span className="leading-relaxed whitespace-pre-wrap break-all">{line.text}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-4 bg-zinc-900/50 border border-zinc-800/80 rounded-lg text-xs text-zinc-500 text-center">
                    {diffResult?.message || "无上一历史版本进行比对。"}
                  </div>
                )}
              </div>

              {/* History snapshots list */}
              <div>
                <h4 className="text-xs font-semibold text-zinc-300 mb-2">该 URL 历史快照版本记录 ({history.length})</h4>
                <div className="space-y-2">
                  {history.map((snap, idx) => (
                    <div key={snap.id} className="p-3 bg-zinc-900/50 border border-zinc-800/80 rounded flex items-center justify-between text-xs">
                      <div>
                        <span className="font-mono text-zinc-300">版本 #{history.length - idx}</span>
                        <span className="text-zinc-500 text-[11px] ml-2">抓取于 {snap.fetched_at}</span>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
                        HTTP {snap.status_code}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 7. Metadata View */}
          {activeTab === "metadata" && (
            <div className="max-w-3xl mx-auto">
              <pre className="p-4 bg-zinc-900 border border-zinc-800 rounded-lg text-xs font-mono text-zinc-300 whitespace-pre-wrap overflow-x-auto">
                {JSON.stringify(
                  {
                    id: doc.id,
                    url: doc.url,
                    domain: doc.domain,
                    type: doc.type,
                    language: doc.language,
                    content_hash: doc.content_hash,
                    created_at: doc.created_at,
                    metadata: typeof doc.metadata_json === "string" ? JSON.parse(doc.metadata_json) : doc.metadata_json
                  },
                  null,
                  2
                )}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

import React, { useState, useEffect } from "react";
import { Project, SiteInspectionResult, CrawlJobConfig, PluginItem } from "../../types";
import { api } from "../../services/api";
import {
  X, Globe, Sparkles, Layers, Sliders, Play, CheckCircle2, AlertCircle,
  Zap, Code2, HelpCircle, TestTube2, BookOpen, Check
} from "lucide-react";

interface CrawlWizardProps {
  project: Project;
  isOpen: boolean;
  onClose: () => void;
  onJobStarted: (jobId: string) => void;
  onOpenGuide?: () => void;
}

export const CrawlWizard: React.FC<CrawlWizardProps> = ({
  project,
  isOpen,
  onClose,
  onJobStarted,
  onOpenGuide
}) => {
  const [urlInput, setUrlInput] = useState("");
  const [jobName, setJobName] = useState(`${project.name} - 采集任务`);
  const [inspecting, setInspecting] = useState(false);
  const [inspection, setInspection] = useState<SiteInspectionResult | null>(null);

  // Top Mode Switch: Traditional (No-AI) vs AI-Assisted
  const [crawlMode, setCrawlMode] = useState<"traditional" | "ai_assisted">("traditional");

  // Strategy in Traditional mode
  const [strategy, setStrategy] = useState<"article" | "website" | "custom_css" | "plugin" | "video">("article");
  const [plugins, setPlugins] = useState<PluginItem[]>([]);
  const [selectedPluginId, setSelectedPluginId] = useState("");

  // Custom CSS Rule inputs
  const [cssTitle, setCssTitle] = useState("h1, .title, .entry-title");
  const [cssContent, setCssContent] = useState("article, .post-content, .entry-content, .content");
  const [cssAuthor, setCssAuthor] = useState(".author, .byline, [rel='author']");
  const [cssDate, setCssDate] = useState("time, .post-date, .published");
  const [testingRule, setTestingRule] = useState(false);
  const [ruleTestResult, setRuleTestResult] = useState<any>(null);

  // Config State
  const [scope, setScope] = useState("domain");
  const [scopeRegex, setScopeRegex] = useState("");
  const [maxDepth, setMaxDepth] = useState(2);
  const [maxPages, setMaxPages] = useState(100);
  const [preset, setPreset] = useState<"gentle" | "balanced" | "fast">("balanced");
  const [fetchMode, setFetchMode] = useState<"fast" | "smart" | "browser">("smart");
  const [enableAiSummary, setEnableAiSummary] = useState(true);
  const [loading, setLoading] = useState(false);

  // Load plugins on mount
  useEffect(() => {
    if (isOpen) {
      api.getPlugins().then((data) => {
        setPlugins(data);
        const firstRulePlugin = data.find((p) => p.type === "rule" && p.enabled);
        if (firstRulePlugin) {
          setSelectedPluginId(firstRulePlugin.id);
        }
      }).catch(() => {});
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleInspect = async () => {
    const firstUrl = urlInput.trim().split("\n")[0];
    if (!firstUrl || !firstUrl.startsWith("http")) return;
    setInspecting(true);
    setInspection(null);
    try {
      const res = await api.inspectUrl(firstUrl);
      setInspection(res);
      if (res.needs_browser) {
        setFetchMode("smart");
      }
    } catch {
      setInspection({ success: false, error: "无法连接到该站点" });
    } finally {
      setInspecting(false);
    }
  };

  const handleFillDemo = () => {
    setUrlInput("https://developer.mozilla.org/zh-CN/docs/Web/HTTP");
    setJobName(`${project.name} - MDN Web文档示例抓取`);
    setScope("path");
    setMaxDepth(1);
    setMaxPages(20);
    setStrategy("article");
  };

  const handleTestRule = async () => {
    const firstUrl = urlInput.trim().split("\n")[0];
    if (!firstUrl || !firstUrl.startsWith("http")) {
      alert("请先在上方输入至少一个有效的 HTTP/HTTPS URL 以便进行实时规则测试");
      return;
    }

    setTestingRule(true);
    setRuleTestResult(null);
    try {
      const res = await api.testRule(firstUrl, {
        title: cssTitle,
        content: cssContent,
        author: cssAuthor,
        date: cssDate
      });
      setRuleTestResult(res);
    } catch (e: any) {
      setRuleTestResult({ success: false, error: e.message });
    } finally {
      setTestingRule(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const urls = urlInput
      .split("\n")
      .map((u) => u.trim())
      .filter((u) => u.startsWith("http"));

    if (urls.length === 0) {
      alert("请输入至少一个有效的 HTTP/HTTPS URL");
      return;
    }

    // Determine adapter_id
    let resolvedAdapterId = "auto";
    if (strategy === "custom_css") {
      resolvedAdapterId = `rule:${JSON.stringify({
        title: cssTitle,
        content: cssContent,
        author: cssAuthor,
        date: cssDate
      })}`;
    } else if (strategy === "plugin" && selectedPluginId) {
      resolvedAdapterId = `plugin:${selectedPluginId}`;
    } else {
      resolvedAdapterId = strategy;
    }

    setLoading(true);
    try {
      const isAiEnabled = crawlMode === "ai_assisted" ? enableAiSummary : false;

      const config: CrawlJobConfig = {
        scope,
        scope_regex: scopeRegex || undefined,
        max_depth: maxDepth,
        max_pages: maxPages,
        preset,
        max_concurrent: preset === "fast" ? 25 : preset === "gentle" ? 3 : 10,
        domain_concurrent: preset === "fast" ? 6 : preset === "gentle" ? 1 : 3,
        domain_delay_ms: preset === "fast" ? 100 : preset === "gentle" ? 1500 : 500,
        fetch_mode: fetchMode,
        content_types: ["article", "markdown"],
        adapter_id: resolvedAdapterId,
        enable_ai_summary: isAiEnabled
      };

      const job = await api.createCrawlJob({
        project_id: project.id,
        name: jobName,
        urls,
        config
      });

      onJobStarted(job.id);
      onClose();
    } catch (err: any) {
      alert(`创建采集任务失败: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-2xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between shrink-0 bg-zinc-950/40">
          <div className="flex items-center gap-2.5">
            <Globe size={18} className="text-zinc-300" />
            <div>
              <h2 className="text-sm font-semibold text-zinc-100">发起内容采集任务</h2>
              <p className="text-[11px] text-zinc-400">项目：{project.name}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {onOpenGuide && (
              <button
                type="button"
                onClick={onOpenGuide}
                className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs rounded-md flex items-center gap-1 transition-colors"
                title="查看使用教程"
              >
                <BookOpen size={13} className="text-emerald-400" />
                <span>新手指南</span>
              </button>
            )}
            <button onClick={onClose} className="p-1 text-zinc-400 hover:text-zinc-200 rounded">
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5">
          {/* Top Mode Selection Cards: Traditional vs AI Assisted */}
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-2">选择采集作业模式</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setCrawlMode("traditional")}
                className={`p-3 rounded-lg border text-left transition-all ${
                  crawlMode === "traditional"
                    ? "bg-zinc-800/90 border-emerald-500/80 shadow-sm ring-1 ring-emerald-500/40"
                    : "bg-zinc-950/60 border-zinc-800 hover:border-zinc-700"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5 font-semibold text-xs text-zinc-100">
                    <Zap size={15} className="text-emerald-400" />
                    <span>⚡ 传统常规采集 (无需 AI)</span>
                  </div>
                  {crawlMode === "traditional" && (
                    <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                  )}
                </div>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  零 Token 消耗 / 纯本地高速运行 / 规则与算法驱动 / 无需任何 API Key 配置
                </p>
              </button>

              <button
                type="button"
                onClick={() => setCrawlMode("ai_assisted")}
                className={`p-3 rounded-lg border text-left transition-all ${
                  crawlMode === "ai_assisted"
                    ? "bg-zinc-800/90 border-purple-500/80 shadow-sm ring-1 ring-purple-500/40"
                    : "bg-zinc-950/60 border-zinc-800 hover:border-zinc-700"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-1.5 font-semibold text-xs text-zinc-100">
                    <Sparkles size={15} className="text-purple-400" />
                    <span>✨ AI 协作增强采集</span>
                  </div>
                  {crawlMode === "ai_assisted" && (
                    <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                  )}
                </div>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  在常规抓取基础上，后台大模型异步自动提炼要点、生成摘要与核心标签
                </p>
              </button>
            </div>
          </div>

          {/* Job Name */}
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">任务名称</label>
            <input
              type="text"
              required
              value={jobName}
              onChange={(e) => setJobName(e.target.value)}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
            />
          </div>

          {/* Seed URLs & Quick Demo Fill */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-medium text-zinc-300">
                采集入口 URL <span className="text-zinc-500">(每行一个，支持多条)</span>
              </label>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleFillDemo}
                  className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1 font-medium"
                >
                  <Play size={11} className="fill-emerald-400 stroke-none" />
                  <span>💡 填入测试示例</span>
                </button>
                <button
                  type="button"
                  onClick={handleInspect}
                  disabled={inspecting || !urlInput.trim()}
                  className="text-xs text-zinc-300 hover:text-white flex items-center gap-1 font-medium disabled:opacity-40"
                >
                  <Sparkles size={13} className="text-amber-400" />
                  <span>{inspecting ? "分析中..." : "探测站点结构"}</span>
                </button>
              </div>
            </div>
            <textarea
              rows={3}
              required
              placeholder="https://example.com/&#10;https://example.com/news/"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-md p-3 text-xs font-mono text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-500 resize-none"
            />
          </div>

          {/* Site Inspection Card */}
          {inspection && (
            <div className="p-3 bg-zinc-950/80 border border-zinc-800 rounded-lg text-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-zinc-200 flex items-center gap-1.5">
                  {inspection.success ? (
                    <CheckCircle2 size={14} className="text-emerald-400" />
                  ) : (
                    <AlertCircle size={14} className="text-rose-400" />
                  )}
                  <span>站点预检报告</span>
                </span>
                {inspection.status_code && (
                  <span className="text-[11px] font-mono text-zinc-400">
                    HTTP {inspection.status_code} ({inspection.response_time_ms}ms)
                  </span>
                )}
              </div>

              {inspection.success ? (
                <div className="grid grid-cols-2 gap-2 text-[11px] text-zinc-400 pt-1">
                  <div>识别标题: <span className="text-zinc-200">{inspection.title || "无"}</span></div>
                  <div>内容类型: <span className="text-zinc-200">{inspection.detected_type}</span></div>
                  <div>发现外链: <span className="text-zinc-200">{inspection.total_links_found} 条</span></div>
                  <div>JS 依赖需求: <span className={inspection.needs_browser ? "text-amber-400" : "text-emerald-400"}>
                    {inspection.needs_browser ? "高 (需浏览器渲染)" : "低 (HTTP 即可)"}
                  </span></div>
                </div>
              ) : (
                <div className="text-rose-400 text-xs">{inspection.error}</div>
              )}
            </div>
          )}

          {/* Extraction Strategy (Pure Rule / Custom CSS / Built-in) */}
          <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <label className="block text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
                <Sliders size={14} className="text-zinc-400" />
                <span>数据抽取策略 (Extractor Strategy)</span>
              </label>
              <span className="text-[11px] text-zinc-500">决定如何从网页中提取标题与正文</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              <label className={`flex items-start gap-2.5 p-2.5 rounded-md border cursor-pointer transition-colors ${
                strategy === "article" ? "bg-zinc-900 border-zinc-600 text-zinc-100" : "bg-zinc-900/40 border-zinc-800/80 text-zinc-400 hover:text-zinc-200"
              }`}>
                <input
                  type="radio"
                  name="strategy"
                  value="article"
                  checked={strategy === "article"}
                  onChange={() => setStrategy("article")}
                  className="mt-0.5"
                />
                <div>
                  <div className="font-semibold text-xs text-zinc-200">智能通用文章提取 (推荐)</div>
                  <div className="text-[11px] text-zinc-400 mt-0.5">Trafilatura 算法，自动识别正文，免配规则</div>
                </div>
              </label>

              <label className={`flex items-start gap-2.5 p-2.5 rounded-md border cursor-pointer transition-colors ${
                strategy === "website" ? "bg-zinc-900 border-zinc-600 text-zinc-100" : "bg-zinc-900/40 border-zinc-800/80 text-zinc-400 hover:text-zinc-200"
              }`}>
                <input
                  type="radio"
                  name="strategy"
                  value="website"
                  checked={strategy === "website"}
                  onChange={() => setStrategy("website")}
                  className="mt-0.5"
                />
                <div>
                  <div className="font-semibold text-xs text-zinc-200">整站页面与外链归档</div>
                  <div className="text-[11px] text-zinc-400 mt-0.5">抓取全站所有网页结构并保留站内拓扑</div>
                </div>
              </label>

              <label className={`flex items-start gap-2.5 p-2.5 rounded-md border cursor-pointer transition-colors ${
                strategy === "custom_css" ? "bg-zinc-900 border-zinc-600 text-zinc-100" : "bg-zinc-900/40 border-zinc-800/80 text-zinc-400 hover:text-zinc-200"
              }`}>
                <input
                  type="radio"
                  name="strategy"
                  value="custom_css"
                  checked={strategy === "custom_css"}
                  onChange={() => setStrategy("custom_css")}
                  className="mt-0.5"
                />
                <div>
                  <div className="font-semibold text-xs text-zinc-200 flex items-center gap-1.5">
                    <Code2 size={13} className="text-amber-400" />
                    <span>自定义 CSS 选择器提取</span>
                  </div>
                  <div className="text-[11px] text-zinc-400 mt-0.5">现场配置并在线测试，精准抽取特定字段</div>
                </div>
              </label>

              <label className={`flex items-start gap-2.5 p-2.5 rounded-md border cursor-pointer transition-colors ${
                strategy === "plugin" ? "bg-zinc-900 border-zinc-600 text-zinc-100" : "bg-zinc-900/40 border-zinc-800/80 text-zinc-400 hover:text-zinc-200"
              }`}>
                <input
                  type="radio"
                  name="strategy"
                  value="plugin"
                  checked={strategy === "plugin"}
                  onChange={() => setStrategy("plugin")}
                  className="mt-0.5"
                />
                <div>
                  <div className="font-semibold text-xs text-zinc-200">选用已安装站点规则插件</div>
                  <div className="text-[11px] text-zinc-400 mt-0.5">使用规则库中的知乎、微信等专用插件</div>
                </div>
              </label>
            </div>

            {/* Custom CSS Inlined Box */}
            {strategy === "custom_css" && (
              <div className="p-3 bg-zinc-900/80 border border-zinc-700/80 rounded-lg space-y-3 mt-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-amber-300 flex items-center gap-1">
                    <Code2 size={14} />
                    <span>现场 CSS 选择器规则配置</span>
                  </span>
                  <button
                    type="button"
                    onClick={handleTestRule}
                    disabled={testingRule}
                    className="px-2.5 py-1 bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/30 rounded text-[11px] font-semibold flex items-center gap-1 transition-colors"
                  >
                    <TestTube2 size={12} />
                    <span>{testingRule ? "测试解析中..." : "🧪 实时测试选择器"}</span>
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <label className="block text-[11px] text-zinc-400 mb-1">标题选择器 (Title)</label>
                    <input
                      type="text"
                      value={cssTitle}
                      onChange={(e) => setCssTitle(e.target.value)}
                      placeholder="h1, .title"
                      className="w-full bg-zinc-950 border border-zinc-700 rounded px-2.5 py-1.5 font-mono text-[11px] text-zinc-100 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-zinc-400 mb-1">正文选择器 (Content)</label>
                    <input
                      type="text"
                      value={cssContent}
                      onChange={(e) => setCssContent(e.target.value)}
                      placeholder="article, .post-content"
                      className="w-full bg-zinc-950 border border-zinc-700 rounded px-2.5 py-1.5 font-mono text-[11px] text-zinc-100 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-zinc-400 mb-1">作者选择器 (可选)</label>
                    <input
                      type="text"
                      value={cssAuthor}
                      onChange={(e) => setCssAuthor(e.target.value)}
                      placeholder=".author, [rel='author']"
                      className="w-full bg-zinc-950 border border-zinc-700 rounded px-2.5 py-1.5 font-mono text-[11px] text-zinc-100 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-zinc-400 mb-1">发布日期选择器 (可选)</label>
                    <input
                      type="text"
                      value={cssDate}
                      onChange={(e) => setCssDate(e.target.value)}
                      placeholder="time, .post-date"
                      className="w-full bg-zinc-950 border border-zinc-700 rounded px-2.5 py-1.5 font-mono text-[11px] text-zinc-100 focus:outline-none"
                    />
                  </div>
                </div>

                {/* Inline Test Result */}
                {ruleTestResult && (
                  <div className="p-2.5 bg-zinc-950 border border-zinc-800 rounded text-[11px] space-y-1">
                    {ruleTestResult.success ? (
                      <div>
                        <div className="flex items-center gap-1.5 text-emerald-400 font-semibold mb-1">
                          <CheckCircle2 size={13} />
                          <span>测试抓取成功！</span>
                        </div>
                        <div className="text-zinc-300"><span className="text-zinc-500">识别标题：</span>{ruleTestResult.title || "(未匹配到标题)"}</div>
                        <div className="text-zinc-300"><span className="text-zinc-500">作者信息：</span>{ruleTestResult.author || "无"}</div>
                        <div className="text-zinc-300"><span className="text-zinc-500">正文字数：</span>{ruleTestResult.text_length} 字</div>
                        {ruleTestResult.text_preview && (
                          <div className="mt-1 text-zinc-400 p-1.5 bg-zinc-900 rounded font-mono text-[10px] line-clamp-2">
                            {ruleTestResult.text_preview}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-rose-400 flex items-center gap-1.5">
                        <AlertCircle size={13} />
                        <span>测试抓取失败: {ruleTestResult.error}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Plugin Select Dropdown */}
            {strategy === "plugin" && (
              <div className="p-3 bg-zinc-900/60 border border-zinc-800 rounded-lg space-y-2">
                <label className="block text-[11px] text-zinc-400">选择要应用的站点插件</label>
                <select
                  value={selectedPluginId}
                  onChange={(e) => setSelectedPluginId(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-700 rounded px-3 py-2 text-xs text-zinc-100 focus:outline-none"
                >
                  {plugins.filter((p) => p.type === "rule" || p.rules).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.id}) - {p.description || "自定义规则"}
                    </option>
                  ))}
                  {plugins.filter((p) => p.type === "rule" || p.rules).length === 0 && (
                    <option value="">暂无规则插件，可前往左侧「规则与插件」添加</option>
                  )}
                </select>
              </div>
            )}
          </div>

          {/* Crawl Scope & Depth with Explanations */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-zinc-300">采集范围 (Scope)</label>
              </div>
              <select
                value={scope}
                onChange={(e) => setScope(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-zinc-500"
              >
                <option value="domain">当前域名 (推荐 - 不越界外链)</option>
                <option value="path">当前目录及下级路径</option>
                <option value="subdomain">主域名及所有二级子域</option>
                <option value="page">仅抓取指定页面 (Depth 0)</option>
                <option value="regex">自定义正则规则</option>
              </select>
              <p className="text-[10px] text-zinc-500 mt-1">控制爬虫是否顺着内链扩展</p>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-zinc-300">抓取层级深度 (Depth)</label>
              </div>
              <select
                value={maxDepth}
                onChange={(e) => setMaxDepth(Number(e.target.value))}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-zinc-500"
              >
                <option value={0}>0 (仅初始 URL，不点开任何链接)</option>
                <option value={1}>1 (初始 URL + 直接内链)</option>
                <option value={2}>2 (向内挖掘 2 层 - 推荐)</option>
                <option value={3}>3 (向内挖掘 3 层)</option>
                <option value={5}>5 (深度整站爬取)</option>
              </select>
              <p className="text-[10px] text-zinc-500 mt-1">深度 2 可覆盖绝大多数文章列表与正文</p>
            </div>
          </div>

          {/* Page Limit & Concurrency Preset */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">最大抓取页面数限制</label>
              <select
                value={maxPages}
                onChange={(e) => setMaxPages(Number(e.target.value))}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-zinc-500"
              >
                <option value={20}>20 篇 (快速体验)</option>
                <option value={50}>50 篇</option>
                <option value={100}>100 篇 (常规)</option>
                <option value={500}>500 篇</option>
                <option value={1000}>1,000 篇</option>
                <option value={5000}>5,000 篇</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">频控策略预设</label>
              <select
                value={preset}
                onChange={(e) => setPreset(e.target.value as any)}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-zinc-500"
              >
                <option value="balanced">均衡 (并发 10 / 域名延迟 500ms)</option>
                <option value="gentle">温和保护 (并发 3 / 延迟 1500ms，防风控)</option>
                <option value="fast">极速模式 (并发 25 / 延迟 100ms)</option>
              </select>
            </div>
          </div>

          {/* Fetch Mode (Fast vs Smart vs Browser) */}
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">网页抓取引擎 (Fetcher Engine)</label>
            <select
              value={fetchMode}
              onChange={(e) => setFetchMode(e.target.value as any)}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-zinc-500"
            >
              <option value="smart">Smart 智能嗅探 (HTTP 优先，发现需要 JS 自动无缝降级到浏览器渲染)</option>
              <option value="fast">Fast 极速模式 (纯异步 HTTP 网络请求，性能最高)</option>
              <option value="browser">Browser 真实浏览器渲染 (Playwright Chromium，解决动态加载)</option>
            </select>
            <p className="text-[10px] text-zinc-500 mt-1">遇到 SPA 单页应用或正文显示为空时，切换为 Browser 即可完整渲染</p>
          </div>

          {/* AI Pipeline Options (Only shown or highlighted if AI mode enabled) */}
          {crawlMode === "ai_assisted" && (
            <div className="p-3 bg-purple-950/20 border border-purple-800/40 rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Sparkles size={16} className="text-purple-400 shrink-0" />
                <div>
                  <div className="text-xs font-medium text-purple-200">启用 AI 异步摘要流水线</div>
                  <div className="text-[11px] text-zinc-400">
                    页面清洗入库后，后台自动调用大模型生成中文要点与关键词标签（可在「系统设置」配置 Key）
                  </div>
                </div>
              </div>
              <input
                type="checkbox"
                checked={enableAiSummary}
                onChange={(e) => setEnableAiSummary(e.target.checked)}
                className="w-4 h-4 rounded bg-zinc-900 border-zinc-700 text-purple-500 focus:ring-0 cursor-pointer"
              />
            </div>
          )}

          {crawlMode === "traditional" && (
            <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg flex items-center gap-2 text-[11px] text-zinc-400">
              <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
              <span>当前为纯传统规则采集模式，已完全停用 AI 流水线，100% 本地运算，零外部网络交互。</span>
            </div>
          )}
        </form>

        {/* Footer Actions */}
        <div className="px-6 py-3 border-t border-zinc-800 bg-zinc-950 flex items-center justify-between shrink-0">
          <div className="text-[11px] text-zinc-500">
            {crawlMode === "traditional" ? "⚡ 纯本地极速规则采集" : "✨ AI 协作增强模式"}
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-md transition-colors"
            >
              取消
            </button>
            <button
              type="button"
              disabled={loading || !urlInput.trim()}
              onClick={handleSubmit}
              className="px-4 py-1.5 bg-zinc-100 text-zinc-900 hover:bg-white text-xs font-semibold rounded-md shadow-sm transition-all flex items-center gap-1.5 active:scale-95 disabled:opacity-50"
            >
              <Play size={13} className="fill-zinc-900 stroke-none" />
              <span>{loading ? "启动中..." : "开始采集任务"}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

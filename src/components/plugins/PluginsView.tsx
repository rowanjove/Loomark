import React, { useState, useEffect } from "react";
import { PluginItem, PresetPluginItem } from "../../types";
import { api } from "../../services/api";
import {
  Boxes, CheckCircle2, Plus, Code2, Globe, Trash2,
  RefreshCw, Play, X, ExternalLink, Sliders, Sparkles, AlertTriangle, ArrowRight, Check,
  Download, Upload, BookOpen
} from "lucide-react";

export const PluginsView: React.FC = () => {
  const [plugins, setPlugins] = useState<PluginItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isTestOpen, setIsTestOpen] = useState(false);

  // Preset Store state (PRD Section 81, 114)
  const [isPresetsOpen, setIsPresetsOpen] = useState(false);
  const [presetList, setPresetList] = useState<PresetPluginItem[]>([]);
  const [loadingPresets, setLoadingPresets] = useState(false);
  const [installingPreset, setInstallingPreset] = useState<string | null>(null);

  // Import plugin state
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [importContent, setImportContent] = useState("");
  const [importing, setImporting] = useState(false);

  // Create plugin form
  const [pluginId, setPluginId] = useState("");
  const [pluginName, setPluginName] = useState("");
  const [matchPattern, setMatchPattern] = useState("");
  const [desc, setDesc] = useState("");
  const [selTitle, setSelTitle] = useState("h1");
  const [selContent, setSelContent] = useState("article, .post-content, .entry-content");
  const [selAuthor, setSelAuthor] = useState(".author, .byline, [rel='author']");
  const [selDate, setSelDate] = useState("time, .post-date, .published");


  // Test rule state
  const [testUrl, setTestUrl] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);

  // AI Selector Repair state (PRD Section 30)
  const [isRepairOpen, setIsRepairOpen] = useState(false);
  const [repairTarget, setRepairTarget] = useState<PluginItem | null>(null);
  const [repairUrl, setRepairUrl] = useState("");
  const [repairing, setRepairing] = useState(false);
  const [repairResult, setRepairResult] = useState<any>(null);
  const [applying, setApplying] = useState(false);
  const [appliedSuccess, setAppliedSuccess] = useState(false);

  const handleOpenRepair = (plugin: PluginItem) => {
    setRepairTarget(plugin);
    setRepairUrl("");
    setRepairResult(null);
    setAppliedSuccess(false);
    setIsRepairOpen(true);
  };

  const handleRunRepair = async () => {
    if (!repairTarget || !repairUrl.trim()) return;
    setRepairing(true);
    setRepairResult(null);
    try {
      const res = await api.diagnoseSelectorRepair(repairTarget.id, repairUrl.trim());
      setRepairResult(res);
    } catch (e: any) {
      setRepairResult({ success: false, error: e.message });
    } finally {
      setRepairing(false);
    }
  };

  const handleApplyRepair = async () => {
    if (!repairTarget || !repairResult?.suggested_rules) return;
    setApplying(true);
    try {
      await api.applySelectorRepair(repairTarget.id, repairResult.suggested_rules);
      setAppliedSuccess(true);
      loadPlugins();
      setTimeout(() => {
        setIsRepairOpen(false);
      }, 1500);
    } catch (e: any) {
      alert(`应用修补规则失败: ${e.message}`);
    } finally {
      setApplying(false);
    }
  };

  const loadPlugins = async () => {
    setLoading(true);
    try {
      const data = await api.getPlugins();
      setPlugins(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenPresets = async () => {
    setIsPresetsOpen(true);
    setLoadingPresets(true);
    try {
      const presets = await api.getPresetPlugins();
      setPresetList(presets);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingPresets(false);
    }
  };

  const handleInstallPreset = async (presetId: string) => {
    setInstallingPreset(presetId);
    try {
      await api.installPresetPlugin(presetId);
      await loadPlugins();
    } catch (e: any) {
      alert(`安装预置插件失败: ${e.message}`);
    } finally {
      setInstallingPreset(null);
    }
  };

  const handleExportPlugin = async (pluginId: string) => {
    try {
      const data = await api.exportPlugin(pluginId);
      const jsonStr = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonStr], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${pluginId}.loomark-plugin.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(`导出插件失败: ${e.message}`);
    }
  };

  const handleImportPlugin = async () => {
    if (!importContent.trim()) return;
    setImporting(true);
    try {
      const parsed = JSON.parse(importContent);
      await api.importPlugin(parsed);
      await loadPlugins();
      setIsImportOpen(false);
      setImportContent("");
    } catch (e: any) {
      alert(`导入失败: ${e.message}`);
    } finally {
      setImporting(false);
    }
  };

  useEffect(() => {
    loadPlugins();
  }, []);


  const handleToggle = async (id: string, current: boolean) => {
    await api.togglePlugin(id, !current);
    loadPlugins();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除此自定义插件吗？")) return;
    try {
      await api.deletePlugin(id);
      loadPlugins();
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleCreatePlugin = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createPlugin({
        id: pluginId.trim() || undefined,
        name: pluginName.trim(),
        match: matchPattern.split(",").map((s) => s.trim()).filter(Boolean),
        description: desc.trim(),
        rules: {
          title: selTitle.trim(),
          content: selContent.trim(),
          author: selAuthor.trim(),
          published_at: selDate.trim()
        },
        enabled: true
      });
      setIsCreateOpen(false);
      setPluginName("");
      setMatchPattern("");
      setDesc("");
      loadPlugins();
    } catch (e: any) {
      alert(`创建插件失败: ${e.message}`);
    }
  };

  const handleRunTest = async () => {
    if (!testUrl.trim()) return;
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.testRule(testUrl.trim(), {
        title: selTitle.trim(),
        content: selContent.trim(),
        author: selAuthor.trim(),
        published_at: selDate.trim()
      });
      setTestResult(res);
    } catch (e: any) {
      setTestResult({ success: false, error: e.message });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-zinc-950 p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Top Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
              <Boxes size={20} className="text-sky-400" />
              <span>插件与适配器中心 (Plugin & Rule Ecosystem)</span>
            </h1>
            <p className="text-xs text-zinc-400 mt-1">
              两级 Adapter 机制：专属站点插件规则 → 通用文章适配器 → 通用整站兜底。
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={handleOpenPresets}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-sky-950/40 hover:bg-sky-900/50 border border-sky-800/60 text-sky-300 text-xs font-medium rounded-md transition-colors"
            >
              <BookOpen size={13} />
              <span>精选规则库 (Presets)</span>
            </button>
            <button
              onClick={() => setIsImportOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-zinc-100 text-xs font-medium rounded-md transition-colors"
            >
              <Upload size={13} />
              <span>导入规则包</span>
            </button>
            <button
              onClick={() => setIsTestOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 hover:text-zinc-100 text-xs font-medium rounded-md transition-colors"
            >
              <Code2 size={13} />
              <span>在线规则测试器</span>
            </button>
            <button
              onClick={() => setIsCreateOpen(true)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-zinc-100 text-zinc-900 hover:bg-white text-xs font-semibold rounded-md shadow-xs transition-all"
            >
              <Plus size={14} />
              <span>新建规则插件</span>
            </button>
          </div>
        </div>

        {/* Plugins Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {plugins.map((plugin) => (
            <div key={plugin.id} className="p-5 bg-zinc-900/60 border border-zinc-800 rounded-xl space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-zinc-100">{plugin.name}</h3>
                    {plugin.is_builtin && (
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-400">
                        内置
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-[10px] font-mono text-zinc-400 mt-0.5">
                    <span>v{plugin.version}</span>
                    <span>•</span>
                    <span>{plugin.type.toUpperCase()}</span>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleToggle(plugin.id, plugin.enabled)}
                    className={`flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded transition-colors ${
                      plugin.enabled
                        ? "text-emerald-400 bg-emerald-950/40 border border-emerald-800/40"
                        : "text-zinc-500 bg-zinc-800/60"
                    }`}
                  >
                    <CheckCircle2 size={12} />
                    <span>{plugin.enabled ? "已启用" : "已禁用"}</span>
                  </button>

                  <button
                    onClick={() => handleExportPlugin(plugin.id)}
                    className="p-1 text-zinc-400 hover:text-zinc-200 rounded hover:bg-zinc-800"
                    title="导出规则 (.loomark-plugin.json)"
                  >
                    <Download size={13} />
                  </button>

                  {!plugin.is_builtin && plugin.type === "rule" && (
                    <button
                      onClick={() => handleOpenRepair(plugin)}
                      className="p-1 text-zinc-400 hover:text-purple-300 rounded hover:bg-purple-950/30"
                      title="选择器诊断与修复"
                    >
                      <Sparkles size={13} />
                    </button>
                  )}

                  {!plugin.is_builtin && (
                    <button
                      onClick={() => handleDelete(plugin.id)}
                      className="p-1 text-zinc-500 hover:text-rose-400 rounded hover:bg-rose-950/20"
                      title="删除此规则插件"
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              </div>

              <p className="text-xs text-zinc-400 leading-relaxed min-h-[32px]">
                {plugin.description || "自定义站点抽取规则。"}
              </p>

              {plugin.rules && (
                <div className="p-2.5 bg-zinc-950/70 border border-zinc-800/70 rounded-lg text-[10px] font-mono text-zinc-400 space-y-1">
                  <div>标题: <span className="text-zinc-300">{plugin.rules.title}</span></div>
                  <div>正文: <span className="text-zinc-300">{plugin.rules.content}</span></div>
                </div>
              )}

              <div className="pt-2 border-t border-zinc-800/60 flex items-center justify-between text-[11px] text-zinc-500 font-mono">
                <span className="truncate max-w-[200px]" title={plugin.match?.join(", ")}>
                  匹配域: {plugin.match?.join(", ") || "*"}
                </span>
                <span>{plugin.author || "Loomark"}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Modal: Create JSON Rule Plugin */}
        {isCreateOpen && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-lg p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
                <div className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
                  <Sliders size={16} className="text-sky-400" />
                  <span>新建免代码 JSON 规则插件 (JSON Rule)</span>
                </div>
                <button onClick={() => setIsCreateOpen(false)} className="text-zinc-400 hover:text-zinc-200">
                  <X size={16} />
                </button>
              </div>

              <form onSubmit={handleCreatePlugin} className="space-y-3.5">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">插件名称</label>
                  <input
                    type="text"
                    required
                    placeholder="如：GitHub Blog 适配器"
                    value={pluginName}
                    onChange={(e) => setPluginName(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">
                    匹配域名通配符 (支持逗号分隔多个)
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="*.example.com, example.com"
                    value={matchPattern}
                    onChange={(e) => setMatchPattern(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">标题 CSS 选择器</label>
                    <input
                      type="text"
                      required
                      value={selTitle}
                      onChange={(e) => setSelTitle(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">正文 CSS 选择器</label>
                    <input
                      type="text"
                      required
                      value={selContent}
                      onChange={(e) => setSelContent(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">作者选择器 (可选)</label>
                    <input
                      type="text"
                      value={selAuthor}
                      onChange={(e) => setSelAuthor(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">日期选择器 (可选)</label>
                    <input
                      type="text"
                      value={selDate}
                      onChange={(e) => setSelDate(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">描述说明</label>
                  <input
                    type="text"
                    placeholder="简要说明此规则针对的网页类型"
                    value={desc}
                    onChange={(e) => setDesc(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
                  />
                </div>

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
                    保存插件规则
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Rule Tester */}
        {isTestOpen && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-2xl p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in-95 duration-150 max-h-[90vh] flex flex-col">
              <div className="flex items-center justify-between pb-3 border-b border-zinc-800 shrink-0">
                <div className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
                  <Code2 size={16} className="text-sky-400" />
                  <span>在线选择器规则测试 (Rule Tester)</span>
                </div>
                <button onClick={() => setIsTestOpen(false)} className="text-zinc-400 hover:text-zinc-200">
                  <X size={16} />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto space-y-4">
                <div className="flex gap-2">
                  <input
                    type="url"
                    placeholder="输入测试网页 URL (如 https://example.com/post)"
                    value={testUrl}
                    onChange={(e) => setTestUrl(e.target.value)}
                    className="flex-1 bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
                  />
                  <button
                    onClick={handleRunTest}
                    disabled={testing}
                    className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 shrink-0 disabled:opacity-50"
                  >
                    <Play size={13} />
                    <span>{testing ? "测试抓取中..." : "运行测试"}</span>
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <label className="text-zinc-400 block mb-1">测试标题规则</label>
                    <input
                      type="text"
                      value={selTitle}
                      onChange={(e) => setSelTitle(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded p-1.5 font-mono text-zinc-200"
                    />
                  </div>
                  <div>
                    <label className="text-zinc-400 block mb-1">测试正文规则</label>
                    <input
                      type="text"
                      value={selContent}
                      onChange={(e) => setSelContent(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded p-1.5 font-mono text-zinc-200"
                    />
                  </div>
                </div>

                {/* Test Result Display */}
                {testResult && (
                  <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-lg space-y-2 text-xs font-mono">
                    <div className="text-zinc-400 font-semibold border-b border-zinc-800 pb-2 flex items-center justify-between">
                      <span>提取预览结果</span>
                      <span className={testResult.success ? "text-emerald-400" : "text-rose-400"}>
                        {testResult.success ? "提取成功" : "提取失败"}
                      </span>
                    </div>

                    {testResult.success ? (
                      <div className="space-y-2 text-zinc-300">
                        <div>
                          <span className="text-zinc-500">抽取标题: </span>
                          <span className="text-zinc-100 font-bold">{testResult.title || "未提取到标题"}</span>
                        </div>
                        <div>
                          <span className="text-zinc-500">作者: </span>
                          <span>{testResult.author || "未提取到作者"}</span>
                        </div>
                        <div>
                          <span className="text-zinc-500">正文长度: </span>
                          <span>{testResult.text_length} 字符</span>
                        </div>
                        <div>
                          <span className="text-zinc-500">正文片段:</span>
                          <p className="mt-1 p-2 bg-zinc-900 rounded text-zinc-300 leading-relaxed">
                            {testResult.text_preview || "正文为空"}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="text-rose-400">{testResult.error}</div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Modal: AI Selector Auto-Repair (PRD Section 30) */}
        {isRepairOpen && repairTarget && (
          <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl animate-in fade-in zoom-in-95 duration-150">
              <div className="p-5 border-b border-zinc-800 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-2">
                  <Sparkles size={18} className="text-purple-400" />
                  <div>
                    <h3 className="text-sm font-semibold text-zinc-100">
                      AI 规则自动修复 (Selector Auto-Repair)
                    </h3>
                    <p className="text-[11px] text-zinc-400">
                      当前针对插件: <span className="font-mono text-zinc-200">{repairTarget.name}</span>
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setIsRepairOpen(false)}
                  className="text-zinc-400 hover:text-zinc-200"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="p-6 space-y-4 overflow-y-auto flex-1 text-xs">
                <div>
                  <label className="block text-zinc-300 font-medium mb-1">
                    改版目标网页 URL (用于提取 DOM 骨架与诊断)
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="url"
                      placeholder="https://example.com/redesigned-article"
                      value={repairUrl}
                      onChange={(e) => setRepairUrl(e.target.value)}
                      className="flex-1 bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
                    />
                    <button
                      onClick={handleRunRepair}
                      disabled={repairing || !repairUrl.trim()}
                      className="flex items-center gap-1.5 px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-semibold rounded-md transition-colors"
                    >
                      {repairing ? <RefreshCw size={13} className="animate-spin" /> : <Sparkles size={13} />}
                      <span>{repairing ? "AI 诊断推导中..." : "开始 AI 诊断"}</span>
                    </button>
                  </div>
                </div>

                {repairResult && (
                  <div className="space-y-4 pt-2">
                    {/* Status Badge */}
                    <div className={`p-3 rounded-lg border flex items-start gap-2.5 ${
                      repairResult.is_degraded
                        ? "bg-amber-950/40 border-amber-800/60 text-amber-200"
                        : "bg-emerald-950/40 border-emerald-800/60 text-emerald-200"
                    }`}>
                      {repairResult.is_degraded ? <AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" /> : <CheckCircle2 size={16} className="text-emerald-400 shrink-0 mt-0.5" />}
                      <div className="space-y-1">
                        <div className="font-semibold">
                          {repairResult.is_degraded ? "检测到选择器退化 (Degraded)" : "选择器运行正常"}
                        </div>
                        <p className="text-[11px] text-zinc-300">
                          {repairResult.repair_reason || "AI 未发现明显结构退化。"}
                        </p>
                        {repairResult.failed_fields?.length > 0 && (
                          <div className="text-[10px] font-mono text-amber-300">
                            失效或过短字段: {repairResult.failed_fields.join(", ")}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Rule Comparison Table */}
                    <div className="bg-zinc-950/70 border border-zinc-800 rounded-lg p-3 space-y-2">
                      <div className="font-semibold text-zinc-300">选择器修复对比</div>
                      <div className="grid grid-cols-3 gap-2 text-[11px] font-mono border-b border-zinc-800/80 pb-1.5 text-zinc-500">
                        <span>字段</span>
                        <span>原选择器 (Old)</span>
                        <span>AI 建议新选择器 (Suggested)</span>
                      </div>
                      {Object.keys(repairResult.suggested_rules || {}).map((field) => {
                        const oldSel = repairResult.old_rules?.[field] || "（未设置）";
                        const newSel = repairResult.suggested_rules?.[field];
                        const isChanged = oldSel !== newSel;
                        return (
                          <div key={field} className="grid grid-cols-3 gap-2 text-[11px] font-mono items-center py-1">
                            <span className="text-zinc-400 font-semibold">{field}</span>
                            <span className="text-zinc-500 truncate">{oldSel}</span>
                            <span className={isChanged ? "text-purple-300 font-bold flex items-center gap-1 truncate" : "text-zinc-400 truncate"}>
                              {newSel}
                              {isChanged && <span className="text-[9px] px-1 bg-purple-950 text-purple-300 border border-purple-800/50 rounded">已更新</span>}
                            </span>
                          </div>
                        );
                      })}
                    </div>

                    {/* Preview Comparison */}
                    <div className="grid grid-cols-2 gap-3 text-[11px]">
                      <div className="p-3 bg-zinc-950/60 border border-zinc-800/80 rounded-lg space-y-1">
                        <div className="text-zinc-500 font-semibold">修补前抽取预览</div>
                        <div className="text-zinc-400">标题: {repairResult.preview_before?.title || "空"}</div>
                        <div className="text-zinc-400">正文字数: {repairResult.preview_before?.content_length || 0} 字符</div>
                      </div>
                      <div className="p-3 bg-zinc-950/60 border border-purple-900/40 rounded-lg space-y-1">
                        <div className="text-purple-300 font-semibold">修补后抽取预览</div>
                        <div className="text-zinc-200 font-bold truncate">标题: {repairResult.preview_after?.title || "空"}</div>
                        <div className="text-emerald-400">正文字数: {repairResult.preview_after?.content_length || 0} 字符</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div className="p-4 border-t border-zinc-800 flex items-center justify-between shrink-0 bg-zinc-900/50">
                <span className="text-[11px] text-zinc-500">
                  经用户确认后应用新规则，默认不自动覆盖。
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setIsRepairOpen(false)}
                    className="px-3.5 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded text-xs"
                  >
                    取消
                  </button>
                  {repairResult?.suggested_rules && (
                    <button
                      onClick={handleApplyRepair}
                      disabled={applying || appliedSuccess}
                      className="flex items-center gap-1.5 px-4 py-1.5 bg-purple-600 hover:bg-purple-500 text-white font-semibold rounded text-xs shadow-xs transition-all disabled:opacity-50"
                    >
                      {appliedSuccess ? <Check size={13} /> : <Sparkles size={13} />}
                      <span>{appliedSuccess ? "已确认并应用！" : (applying ? "正在写入配置..." : "确认应用此修补")}</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Modal: Preset Plugins Store (PRD Section 81, 114) */}
        {isPresetsOpen && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl animate-in fade-in zoom-in-95 duration-150">
              <div className="p-5 border-b border-zinc-800 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-2">
                  <BookOpen size={18} className="text-sky-400" />
                  <h3 className="text-sm font-semibold text-zinc-100">官方精选规则库 (Preset Rule Templates)</h3>
                </div>
                <button onClick={() => setIsPresetsOpen(false)} className="p-1 text-zinc-400 hover:text-zinc-200">
                  <X size={16} />
                </button>
              </div>

              <div className="p-6 overflow-y-auto flex-1 space-y-4">
                <div className="text-xs text-zinc-400 bg-zinc-950 p-3 rounded-lg border border-zinc-800/80">
                  提供开箱即用的主流站点高精准度抽取规则。点击“一键安装”即可将适配器规则注入当前工作区。
                </div>

                {loadingPresets ? (
                  <div className="py-16 text-center text-zinc-500 text-xs flex items-center justify-center gap-2">
                    <RefreshCw size={14} className="animate-spin" />
                    <span>加载精选规则库中...</span>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {presetList.map((preset) => (
                      <div key={preset.id} className="p-4 bg-zinc-950 border border-zinc-800/90 rounded-xl space-y-3 flex flex-col justify-between">
                        <div className="space-y-2">
                          <div className="flex items-start justify-between">
                            <div>
                              <h4 className="text-sm font-bold text-zinc-100">{preset.name}</h4>
                              <div className="text-[10px] font-mono text-zinc-500 mt-0.5">
                                {preset.author} · v{preset.version}
                              </div>
                            </div>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-950/60 text-sky-400 border border-sky-800/40">
                              权限: {preset.permissions?.join(", ") || "network"}
                            </span>
                          </div>

                          <p className="text-xs text-zinc-400 leading-relaxed">
                            {preset.description}
                          </p>

                          <div className="p-2 bg-zinc-900/60 rounded border border-zinc-800/60 text-[10px] font-mono text-zinc-400 space-y-0.5">
                            <div>匹配: <span className="text-zinc-300">{preset.match.join(", ")}</span></div>
                            <div>选择器: <span className="text-zinc-300 truncate block">标题={preset.rules.title}</span></div>
                          </div>
                        </div>

                        <button
                          onClick={() => handleInstallPreset(preset.id)}
                          disabled={installingPreset === preset.id}
                          className="w-full mt-2 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5 disabled:opacity-50"
                        >
                          {installingPreset === preset.id ? (
                            <>
                              <RefreshCw size={12} className="animate-spin" />
                              <span>安装中...</span>
                            </>
                          ) : (
                            <>
                              <CheckCircle2 size={13} className="text-sky-400" />
                              <span>一键安装此规则</span>
                            </>
                          )}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Modal: Import Plugin Package */}
        {isImportOpen && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-lg p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between pb-3 border-b border-zinc-800">
                <div className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
                  <Upload size={16} className="text-sky-400" />
                  <span>导入规则插件包 (Import Plugin)</span>
                </div>
                <button onClick={() => setIsImportOpen(false)} className="p-1 text-zinc-400 hover:text-zinc-200">
                  <X size={16} />
                </button>
              </div>

              <div className="space-y-3 text-xs">
                <p className="text-zinc-400 leading-relaxed">
                  请粘贴或上传外部导出的 <code className="text-zinc-200">.loomark-plugin.json</code> 内容。系统将自动校验 Manifest 规范与规则结构。
                </p>

                <div>
                  <input
                    type="file"
                    accept=".json"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        const reader = new FileReader();
                        reader.onload = (evt) => {
                          setImportContent(evt.target?.result as string || "");
                        };
                        reader.readAsText(file);
                      }
                    }}
                    className="block w-full text-xs text-zinc-400 file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:text-xs file:bg-zinc-800 file:text-zinc-300 hover:file:bg-zinc-700 cursor-pointer"
                  />
                </div>

                <textarea
                  rows={8}
                  value={importContent}
                  onChange={(e) => setImportContent(e.target.value)}
                  placeholder="在此处粘贴 JSON 插件内容..."
                  className="w-full p-3 bg-zinc-950 border border-zinc-800 rounded-lg font-mono text-[11px] text-zinc-200 focus:outline-none focus:border-zinc-500 resize-none"
                />
              </div>

              <div className="pt-2 border-t border-zinc-800 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsImportOpen(false)}
                  className="px-3.5 py-1.5 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-md"
                >
                  取消
                </button>
                <button
                  type="button"
                  onClick={handleImportPlugin}
                  disabled={importing || !importContent.trim()}
                  className="px-4 py-1.5 bg-zinc-100 text-zinc-900 hover:bg-white text-xs font-semibold rounded-md shadow-xs transition-all disabled:opacity-50"
                >
                  {importing ? "正在校验与安装..." : "验证并安装"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};



import React, { useState, useEffect } from "react";
import { api } from "../../services/api";
import { useTheme } from "../../services/theme";
import { Settings, Cpu, HardDrive, Shield, Check, Save, Network, Trash2, Mic, Radio, Sun, Moon } from "lucide-react";

export const SettingsView: React.FC = () => {
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://api.deepseek.com/v1");
  const [model, setModel] = useState("deepseek-chat");
  const [savedMessage, setSavedMessage] = useState(false);
  const [loading, setLoading] = useState(false);

  // Network & Crawler settings (PRD Section 84-85)
  const [userAgent, setUserAgent] = useState("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36");
  const [proxyMode, setProxyMode] = useState<"direct" | "system" | "custom">("direct");
  const [proxyUrl, setProxyUrl] = useState("");

  // ASR Settings (PRD Section 34)
  const [asrEnabled, setAsrEnabled] = useState(false);
  const [asrMode, setAsrMode] = useState<"remote" | "local">("remote");
  const [asrModelSize, setAsrModelSize] = useState("base");
  const [asrDevice, setAsrDevice] = useState("cpu");
  const [remoteAsrBaseUrl, setRemoteAsrBaseUrl] = useState("https://api.openai.com/v1");
  const [remoteAsrApiKey, setRemoteAsrApiKey] = useState("");
  const [remoteAsrModel, setRemoteAsrModel] = useState("whisper-1");

  // Storage cache
  const [clearingCache, setClearingCache] = useState(false);
  const [cacheClearedMsg, setCacheClearedMsg] = useState(false);

  useEffect(() => {
    api.getSettings().then((res) => {
      if (res.ai) {
        setBaseUrl(res.ai.base_url || "https://api.deepseek.com/v1");
        setModel(res.ai.model || "deepseek-chat");
      }
      if (res.crawler) {
        setUserAgent(res.crawler.default_user_agent || "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36");
        setProxyMode(res.crawler.proxy_mode || "direct");
        setProxyUrl(res.crawler.proxy_url || "");
      }
      if (res.asr) {
        setAsrEnabled(Boolean(res.asr.enabled));
        setAsrMode(res.asr.mode || "remote");
        setAsrModelSize(res.asr.model_size || "base");
        setAsrDevice(res.asr.device || "cpu");
        setRemoteAsrBaseUrl(res.asr.remote_base_url || "https://api.openai.com/v1");
        setRemoteAsrModel(res.asr.remote_model || "whisper-1");
      }
    });
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.updateSettings({
        ai: {
          api_key: apiKey.trim() || undefined,
          base_url: baseUrl.trim(),
          model: model.trim()
        },
        crawler: {
          default_user_agent: userAgent.trim(),
          proxy_mode: proxyMode,
          proxy_url: proxyUrl.trim()
        },
        asr: {
          enabled: asrEnabled,
          mode: asrMode,
          model_size: asrModelSize,
          device: asrDevice,
          remote_base_url: remoteAsrBaseUrl.trim(),
          remote_api_key: remoteAsrApiKey.trim() || undefined,
          remote_model: remoteAsrModel.trim()
        }
      });
      setSavedMessage(true);
      setTimeout(() => setSavedMessage(false), 3000);
    } catch (e: any) {
      alert(`保存失败: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleClearCache = async () => {
    if (!confirm("确定要清空已缓存的 AI 抽取结果吗？项目原始网页与已归档文档不会受任何影响。")) return;
    setClearingCache(true);
    try {
      await api.clearCache();
      setCacheClearedMsg(true);
      setTimeout(() => setCacheClearedMsg(false), 3000);
    } catch (e: any) {
      alert(`清空缓存失败: ${e.message}`);
    } finally {
      setClearingCache(false);
    }
  };

  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex-1 overflow-y-auto bg-zinc-950 p-8">
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Title */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
              <Settings size={20} className="text-zinc-400" />
              <span>全局系统设置</span>
            </h1>
            <p className="text-xs text-zinc-400 mt-1">
              配置本地爬虫引擎参数、网络代理、AI 模型服务以及数据存储策略。
            </p>
          </div>

          <button
            type="button"
            onClick={toggleTheme}
            title={theme === "dark" ? "切换为浅色模式" : "切换为深色模式"}
            aria-label={theme === "dark" ? "切换为浅色模式" : "切换为深色模式"}
            className="p-2.5 rounded-lg border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-zinc-100 transition-colors shadow-xs flex items-center justify-center cursor-pointer"
          >
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>

        {/* AI Configuration Section */}
        <section className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-6 space-y-5">
          <div className="flex items-center gap-2.5 pb-3 border-b border-zinc-800">
            <Cpu size={18} className="text-purple-400" />
            <div>
              <h3 className="text-sm font-semibold text-zinc-200">AI 模型与 Provider 配置</h3>
              <p className="text-[11px] text-zinc-400">支持 OpenAI 兼容格式 (DeepSeek, OpenAI, Gemini, Ollama 本地模型等)</p>
            </div>
          </div>

          <form onSubmit={handleSave} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">API Base URL</label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://api.deepseek.com/v1"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
              />
              <span className="text-[10px] text-zinc-500 mt-1 block">
                本地 Ollama 填写：http://localhost:11434/v1
              </span>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">API Key</label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="sk-..."
                className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
              />
              <span className="text-[10px] text-zinc-500 mt-1 block">
                仅在本地会话中保存，绝不上传第三方服务器。
              </span>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1.5">默认模型名称</label>
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="deepseek-chat"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
              />
            </div>

            {/* Network & Proxy (PRD Section 84-85) */}
            <div className="pt-4 border-t border-zinc-800/80 space-y-4">
              <div className="flex items-center gap-2">
                <Network size={16} className="text-sky-400" />
                <span className="text-xs font-semibold text-zinc-200">网络与代理配置 (Proxy & Network)</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-zinc-300 mb-1">网络代理模式</label>
                  <select
                    value={proxyMode}
                    onChange={(e) => setProxyMode(e.target.value as any)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs text-zinc-100 focus:outline-none focus:border-zinc-500"
                  >
                    <option value="direct">直接连接 (Direct)</option>
                    <option value="system">使用系统代理 (System)</option>
                    <option value="custom">自定义代理 (Custom HTTP/SOCKS5)</option>
                  </select>
                </div>

                {proxyMode === "custom" && (
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">自定义代理 URL</label>
                    <input
                      type="text"
                      placeholder="http://127.0.0.1:7890"
                      value={proxyUrl}
                      onChange={(e) => setProxyUrl(e.target.value)}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
                    />
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">自定义 User-Agent</label>
                <input
                  type="text"
                  value={userAgent}
                  onChange={(e) => setUserAgent(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-zinc-500"
                />
              </div>
            </div>

            {/* ASR Speech Recognition Settings (PRD Section 34) */}
            <div className="pt-4 border-t border-zinc-800/80 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Mic size={16} className="text-amber-400" />
                  <div>
                    <span className="text-xs font-semibold text-zinc-200">ASR 语音识别与无字幕转写</span>
                    <p className="text-[10px] text-zinc-400">当抓取到的视频无官方或自动字幕轨时，自动触发音频抽取与语音识别</p>
                  </div>
                </div>

                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={asrEnabled}
                    onChange={(e) => setAsrEnabled(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-9 h-5 bg-zinc-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-amber-600"></div>
                </label>
              </div>

              {asrEnabled && (
                <div className="p-3.5 bg-zinc-950/60 border border-zinc-800 rounded-lg space-y-3 animate-in fade-in duration-150">
                  <div>
                    <label className="block text-xs font-medium text-zinc-300 mb-1">运行模式</label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => setAsrMode("remote")}
                        className={`py-1.5 text-xs rounded border transition-all ${
                          asrMode === "remote"
                            ? "bg-zinc-800 border-zinc-600 text-zinc-100 font-semibold"
                            : "bg-zinc-950 border-zinc-800 text-zinc-400"
                        }`}
                      >
                        远程 ASR API (OpenAI 兼容 / 云端服务)
                      </button>
                      <button
                        type="button"
                        onClick={() => setAsrMode("local")}
                        className={`py-1.5 text-xs rounded border transition-all ${
                          asrMode === "local"
                            ? "bg-zinc-800 border-amber-600/80 text-amber-200 font-semibold"
                            : "bg-zinc-950 border-zinc-800 text-zinc-400"
                        }`}
                      >
                        本地离线 Faster-Whisper (私有无损)
                      </button>
                    </div>
                  </div>

                  {asrMode === "local" ? (
                    <div className="space-y-3 pt-1">
                      <div className="p-2.5 bg-amber-950/30 border border-amber-800/40 rounded text-[11px] text-amber-300 leading-relaxed">
                        注意：本地离线 Faster-Whisper 需要本地已安装 <code>faster-whisper</code> 依赖与 PyTorch 环境，初次识别将自动下载模型权重（几百MB ~ 数GB）。
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-zinc-300 mb-1">本地模型规格</label>
                          <select
                            value={asrModelSize}
                            onChange={(e) => setAsrModelSize(e.target.value)}
                            className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-100 focus:outline-none"
                          >
                            <option value="tiny">Tiny (约 75MB, 极速轻量)</option>
                            <option value="base">Base (约 145MB, 推荐平衡)</option>
                            <option value="small">Small (约 480MB, 高准确度)</option>
                            <option value="medium">Medium (约 1.5GB, 需独立显卡)</option>
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-zinc-300 mb-1">计算硬件设备</label>
                          <select
                            value={asrDevice}
                            onChange={(e) => setAsrDevice(e.target.value)}
                            className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs text-zinc-100 focus:outline-none"
                          >
                            <option value="cpu">CPU 计算 (通用兼容)</option>
                            <option value="cuda">CUDA (NVIDIA 显卡硬件加速)</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3 pt-1">
                      <div>
                        <label className="block text-xs font-medium text-zinc-300 mb-1">远程 ASR Base URL</label>
                        <input
                          type="text"
                          value={remoteAsrBaseUrl}
                          onChange={(e) => setRemoteAsrBaseUrl(e.target.value)}
                          placeholder="https://api.openai.com/v1"
                          className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs font-mono text-zinc-100 focus:outline-none"
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-zinc-300 mb-1">专用 API Key (可选)</label>
                          <input
                            type="password"
                            value={remoteAsrApiKey}
                            onChange={(e) => setRemoteAsrApiKey(e.target.value)}
                            placeholder="留空则沿用全局 Key"
                            className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs font-mono text-zinc-100 focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-zinc-300 mb-1">远程模型标识</label>
                          <input
                            type="text"
                            value={remoteAsrModel}
                            onChange={(e) => setRemoteAsrModel(e.target.value)}
                            placeholder="whisper-1"
                            className="w-full bg-zinc-950 border border-zinc-800 rounded px-2.5 py-1.5 text-xs font-mono text-zinc-100 focus:outline-none"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="pt-3 flex items-center justify-between">
              {savedMessage ? (
                <span className="text-xs text-emerald-400 flex items-center gap-1">
                  <Check size={14} /> 设置已生效保存！
                </span>
              ) : <span />}

              <button
                type="submit"
                disabled={loading}
                className="px-4 py-1.5 bg-zinc-100 text-zinc-900 hover:bg-white text-xs font-semibold rounded-md shadow-xs transition-all flex items-center gap-1.5"
              >
                <Save size={13} />
                <span>{loading ? "保存中..." : "保存全部配置"}</span>
              </button>
            </div>
          </form>
        </section>

        {/* Local Storage & Cache Management (PRD Section 91-92) */}
        <section className="bg-zinc-900/60 border border-zinc-800 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-2.5 pb-3 border-b border-zinc-800">
            <HardDrive size={18} className="text-sky-400" />
            <div>
              <h3 className="text-sm font-semibold text-zinc-200">本地存储与缓存管理 (Storage & Cache Policy)</h3>
              <p className="text-[11px] text-zinc-400">所有网页快照与清洗文本默认本地保存，可随时安全释放 AI 缓存</p>
            </div>
          </div>

          <div className="space-y-3 text-xs text-zinc-300">
            <div className="flex items-center justify-between p-3 bg-zinc-950 rounded-lg border border-zinc-800/80">
              <span>SQLite 数据库引擎</span>
              <span className="font-mono text-zinc-400">WAL Mode (Write-Ahead Logging)</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-zinc-950 rounded-lg border border-zinc-800/80">
              <span>全文索引状态</span>
              <span className="font-mono text-emerald-400">FTS5 Unicode61 Tokenizer</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-zinc-950 rounded-lg border border-zinc-800/80">
              <div>
                <div className="font-medium text-zinc-200">AI 结果缓存清理</div>
                <div className="text-[11px] text-zinc-500 mt-0.5">清空 Hash 记忆，强制重新调用模型</div>
              </div>
              <button
                onClick={handleClearCache}
                disabled={clearingCache}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-zinc-900 hover:bg-rose-950/40 border border-zinc-800 hover:border-rose-800 text-zinc-300 hover:text-rose-300 text-xs rounded transition-colors"
              >
                <Trash2 size={12} />
                <span>{clearingCache ? "清理中..." : cacheClearedMsg ? "缓存已清空" : "清空 AI 缓存"}</span>
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

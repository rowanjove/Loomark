import React, { useState } from "react";
import {
  X, HelpCircle, BookOpen, Layers, Zap, Sparkles, CheckCircle2,
  Globe, Play, ArrowRight, ShieldCheck, Cpu, Code2, AlertTriangle,
  FileText, Search, Download, ExternalLink, RefreshCw
} from "lucide-react";

interface WorkflowGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStartDemo?: () => void;
}

export const WorkflowGuideModal: React.FC<WorkflowGuideModalProps> = ({
  isOpen,
  onClose,
  onStartDemo
}) => {
  const [activeTab, setActiveTab] = useState<"workflow" | "no_ai" | "ai_features" | "faq">("workflow");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between shrink-0 bg-zinc-950/60">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-zinc-700/80 flex items-center justify-center text-zinc-100">
              <BookOpen size={18} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-zinc-100">Loomark 使用教程与快速上手流程</h2>
                <span className="px-2 py-0.5 text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full">
                  新手必读
                </span>
              </div>
              <p className="text-[11px] text-zinc-400">
                支持 100% 纯本地传统规则采集，亦可按需无缝开启 AI 协作增强
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-zinc-400 hover:text-zinc-200 rounded hover:bg-zinc-800 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="px-6 pt-3 border-b border-zinc-800 bg-zinc-950/30 flex gap-2 shrink-0 overflow-x-auto">
          <button
            onClick={() => setActiveTab("workflow")}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition-all ${
              activeTab === "workflow"
                ? "border-zinc-200 text-zinc-100"
                : "border-transparent text-zinc-400 hover:text-zinc-300"
            }`}
          >
            <Layers size={14} />
            <span>5 步核心工作流程</span>
          </button>

          <button
            onClick={() => setActiveTab("no_ai")}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition-all ${
              activeTab === "no_ai"
                ? "border-emerald-400 text-emerald-300 font-semibold"
                : "border-transparent text-zinc-400 hover:text-zinc-300"
            }`}
          >
            <Zap size={14} className="text-emerald-400" />
            <span>⚡ 无需 AI 的常规爬虫指南</span>
          </button>

          <button
            onClick={() => setActiveTab("ai_features")}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition-all ${
              activeTab === "ai_features"
                ? "border-purple-400 text-purple-300 font-semibold"
                : "border-transparent text-zinc-400 hover:text-zinc-300"
            }`}
          >
            <Sparkles size={14} className="text-purple-400" />
            <span>✨ AI 协作增强模式</span>
          </button>

          <button
            onClick={() => setActiveTab("faq")}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition-all ${
              activeTab === "faq"
                ? "border-zinc-200 text-zinc-100"
                : "border-transparent text-zinc-400 hover:text-zinc-300"
            }`}
          >
            <HelpCircle size={14} />
            <span>新手常见问题与避坑 (FAQ)</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 text-xs text-zinc-300 space-y-6">
          {/* TAB 1: WORKFLOW OVERVIEW */}
          {activeTab === "workflow" && (
            <div className="space-y-6">
              {/* Flowchart banner */}
              <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-xl">
                <div className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider mb-3">
                  数据采集全链路图解（5步闭环）
                </div>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-2 items-center text-center">
                  <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 flex flex-col items-center">
                    <span className="w-5 h-5 rounded-full bg-zinc-800 text-zinc-200 text-[10px] font-bold flex items-center justify-center mb-1">1</span>
                    <span className="font-semibold text-zinc-200">新建项目</span>
                    <span className="text-[10px] text-zinc-400 mt-0.5">创建独立数据集</span>
                  </div>
                  <div className="hidden md:flex justify-center text-zinc-600">➔</div>
                  <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 flex flex-col items-center">
                    <span className="w-5 h-5 rounded-full bg-zinc-800 text-zinc-200 text-[10px] font-bold flex items-center justify-center mb-1">2</span>
                    <span className="font-semibold text-zinc-200">配置与发起</span>
                    <span className="text-[10px] text-zinc-400 mt-0.5">网址 / 范围 / 模式</span>
                  </div>
                  <div className="hidden md:flex justify-center text-zinc-600">➔</div>
                  <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 flex flex-col items-center">
                    <span className="w-5 h-5 rounded-full bg-zinc-800 text-zinc-200 text-[10px] font-bold flex items-center justify-center mb-1">3</span>
                    <span className="font-semibold text-zinc-200">采集监控</span>
                    <span className="text-[10px] text-zinc-400 mt-0.5">并发与实时日志</span>
                  </div>
                  <div className="hidden md:flex justify-center text-zinc-600">➔</div>
                  <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 flex flex-col items-center">
                    <span className="w-5 h-5 rounded-full bg-zinc-800 text-zinc-200 text-[10px] font-bold flex items-center justify-center mb-1">4</span>
                    <span className="font-semibold text-zinc-200">查阅与搜索</span>
                    <span className="text-[10px] text-zinc-400 mt-0.5">纯净 Markdown 阅读</span>
                  </div>
                  <div className="hidden md:flex justify-center text-zinc-600">➔</div>
                  <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 flex flex-col items-center">
                    <span className="w-5 h-5 rounded-full bg-zinc-800 text-zinc-200 text-[10px] font-bold flex items-center justify-center mb-1">5</span>
                    <span className="font-semibold text-zinc-200">本地导出</span>
                    <span className="text-[10px] text-zinc-400 mt-0.5">Markdown / CSV</span>
                  </div>
                </div>
              </div>

              {/* Step by step details */}
              <div className="space-y-4">
                <div className="p-4 bg-zinc-950/60 border border-zinc-800/80 rounded-lg flex items-start gap-3.5">
                  <div className="w-7 h-7 rounded-md bg-zinc-800 flex items-center justify-center text-zinc-200 font-bold shrink-0">
                    1
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-xs font-semibold text-zinc-200">第一步：创建采集项目 (Project)</h3>
                    <p className="text-[11px] text-zinc-400 leading-relaxed">
                      项目是用来存放同一类主题或同一个网站数据的归档箱。点击左侧菜单的【新建采集项目】，输入名称（如“科技新闻研究”或“竞品博客追踪”）即可创建。所有抓取到的文章与网页都会保存在该项目内。
                    </p>
                  </div>
                </div>

                <div className="p-4 bg-zinc-950/60 border border-zinc-800/80 rounded-lg flex items-start gap-3.5">
                  <div className="w-7 h-7 rounded-md bg-zinc-800 flex items-center justify-center text-zinc-200 font-bold shrink-0">
                    2
                  </div>
                  <div className="space-y-1.5 flex-1">
                    <h3 className="text-xs font-semibold text-zinc-200">第二步：配置并启动采集任务 (Crawl Job)</h3>
                    <p className="text-[11px] text-zinc-400 leading-relaxed">
                      进入项目后，点击右上角【发起新采集】打开向导窗口：
                    </p>
                    <ul className="list-disc list-inside text-[11px] text-zinc-400 space-y-1 pl-1">
                      <li><strong className="text-zinc-300">输入网址：</strong>贴入要采集的入口链接（支持多行批量输入）。</li>
                      <li><strong className="text-zinc-300">采集模式：</strong>默认为【⚡ 传统常规采集（无需 AI）】，直接开跑，零费用；亦可勾选【✨ AI 协作增强】让模型自动提炼摘要。</li>
                      <li><strong className="text-zinc-300">采集深度 (Depth)：</strong><code className="text-zinc-300">0</code> 代表仅抓取输入的这一页；<code className="text-zinc-300">1~2</code> 代表自动顺着页面里的内链向下深挖 1 到 2 层。</li>
                      <li><strong className="text-zinc-300">抓取引擎：</strong>常规网页保持默认 <code className="text-zinc-300">Smart</code> 即可；若网页需要登录或动态渲染加载，可选择 <code className="text-zinc-300">Browser (Chromium)</code>。</li>
                    </ul>
                  </div>
                </div>

                <div className="p-4 bg-zinc-950/60 border border-zinc-800/80 rounded-lg flex items-start gap-3.5">
                  <div className="w-7 h-7 rounded-md bg-zinc-800 flex items-center justify-center text-zinc-200 font-bold shrink-0">
                    3
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-xs font-semibold text-zinc-200">第三步：实时监控任务进度 (Monitor)</h3>
                    <p className="text-[11px] text-zinc-400 leading-relaxed">
                      任务启动后，点击左侧【采集监控】可实时查看当前下载速率（pages/s）、队列剩余与成功/失败总数。右侧控制台展示详细网络日志，支持一键暂停、继续或对失败 URL 进行重新抓取。
                    </p>
                  </div>
                </div>

                <div className="p-4 bg-zinc-950/60 border border-zinc-800/80 rounded-lg flex items-start gap-3.5">
                  <div className="w-7 h-7 rounded-md bg-zinc-800 flex items-center justify-center text-zinc-200 font-bold shrink-0">
                    4
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-xs font-semibold text-zinc-200">第四步：查阅归档内容与全文检索 (Documents)</h3>
                    <p className="text-[11px] text-zinc-400 leading-relaxed">
                      在【文档归档】中，所有采集回来的网页都已被自动剔除广告、导航和脚本，转换为纯净的标准 Markdown。点击即可打开侧边阅读器，查看文章正文、作者、时间，并使用顶部搜索框进行 SQLite 本地全文毫秒级检索。
                    </p>
                  </div>
                </div>

                <div className="p-4 bg-zinc-950/60 border border-zinc-800/80 rounded-lg flex items-start gap-3.5">
                  <div className="w-7 h-7 rounded-md bg-zinc-800 flex items-center justify-center text-zinc-200 font-bold shrink-0">
                    5
                  </div>
                  <div className="space-y-1">
                    <h3 className="text-xs font-semibold text-zinc-200">第五步：一键本地批量导出 (Export)</h3>
                    <p className="text-[11px] text-zinc-400 leading-relaxed">
                      点击【数据导出】，支持一键将项目内所有内容打包导出为 Markdown 知识库文件夹（直接适配 Obsidian / Notion）、JSON 数据集或 CSV 统计表格，完全离线留存，保证数据自主可控。
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: NO-AI SCRAPER GUIDE */}
          {activeTab === "no_ai" && (
            <div className="space-y-5">
              <div className="p-4 bg-emerald-950/20 border border-emerald-800/40 rounded-xl space-y-2">
                <div className="flex items-center gap-2 text-emerald-300 font-semibold text-xs">
                  <Zap size={16} />
                  <span>不用 AI 能跑吗？能！而且完全满足 100% 网页采集需求</span>
                </div>
                <p className="text-[11px] text-zinc-300 leading-relaxed">
                  本软件底层基于纯本地高性能爬虫引擎（异步 HTTP 协程网络 + Playwright 无头真实浏览器 + Trafilatura 网页正文抽取算法 + SQLite 本地存储）。
                  <strong className="text-emerald-400"> 不需要购买任何大模型 API Key，也不产生任何 Token 费用，开箱即可作为专业本地爬虫工具使用。</strong>
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-lg space-y-2">
                  <div className="flex items-center gap-2 text-zinc-200 font-semibold text-xs">
                    <FileText size={15} className="text-blue-400" />
                    <span>1. 智能通用正文提取 (Trafilatura)</span>
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-relaxed">
                    基于正文密度与 HTML DOM 树算法，自动剔除网页顶部导航、侧边推荐、页尾免责声明与弹窗广告，精准抽取出标题、正文和发布时间。你无需编写一行代码或规则！
                  </p>
                </div>

                <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-lg space-y-2">
                  <div className="flex items-center gap-2 text-zinc-200 font-semibold text-xs">
                    <Globe size={15} className="text-emerald-400" />
                    <span>2. 整站自动化外链深挖 (Site Crawl)</span>
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-relaxed">
                    输入一个博客首页或知识库主页，将“抓取深度”设置为 2，爬虫会自动提取页面中的所有站内内链并向下递归抓取，批量将整站文章归档到本地。
                  </p>
                </div>

                <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-lg space-y-2">
                  <div className="flex items-center gap-2 text-zinc-200 font-semibold text-xs">
                    <Code2 size={15} className="text-amber-400" />
                    <span>3. 自定义 CSS 选择器提取 (现场配置)</span>
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-relaxed">
                    对于特定网站，可在采集向导中勾选【自定义 CSS 选择器】，填入如 <code className="text-zinc-200">h1.title</code> 或 <code className="text-zinc-200">.post-content</code>，点击【测试抓取】即可现场预览抽取的字段，精准可控！
                  </p>
                </div>

                <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-lg space-y-2">
                  <div className="flex items-center gap-2 text-zinc-200 font-semibold text-xs">
                    <ShieldCheck size={15} className="text-purple-400" />
                    <span>4. Playwright 动态渲染支持</span>
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-relaxed">
                    现代网站大量采用 Vue/React 单页动态渲染。只需将抓取模式选为 <code className="text-zinc-200">Browser</code>，引擎将自动调起 Chromium 执行 JavaScript 渲染后再抓取，轻松应对动态网页。
                  </p>
                </div>
              </div>

              <div className="p-3.5 bg-zinc-950 border border-zinc-800 rounded-lg text-[11px] text-zinc-400 flex items-center justify-between">
                <div>
                  <span className="font-semibold text-zinc-200">小提示：</span>
                  在任务向导中，确保选择【⚡ 传统常规采集】，即可完全禁用任何后台 AI 任务，实现纯本地秒级高速抓取。
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: AI ASSISTED MODE */}
          {activeTab === "ai_features" && (
            <div className="space-y-5">
              <div className="p-4 bg-purple-950/20 border border-purple-800/40 rounded-xl space-y-2">
                <div className="flex items-center gap-2 text-purple-300 font-semibold text-xs">
                  <Sparkles size={16} />
                  <span>AI 协作增强：让大模型成为你的智能阅读与研究助理</span>
                </div>
                <p className="text-[11px] text-zinc-300 leading-relaxed">
                  采集完成后，AI 可协助你自动消化成百上千篇网页，提取核心观点、总结要点、分类打标，甚至在你遇到规则失效时自动修补选择器。
                </p>
              </div>

              <div className="space-y-3">
                <div className="p-3.5 bg-zinc-950 border border-zinc-800 rounded-lg space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-zinc-200">① 自动异步生成摘要与核心要点</span>
                    <span className="text-[10px] text-purple-400 font-mono">异步队列·不拖慢爬虫</span>
                  </div>
                  <p className="text-[11px] text-zinc-400">
                    在采集向导中勾选【启用 AI 异步摘要流水线】。爬虫抓取入库后，后台工作进程会自动调用大模型生成中文要点、结论与 5 个关键词标签。
                  </p>
                </div>

                <div className="p-3.5 bg-zinc-950 border border-zinc-800 rounded-lg space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-zinc-200">② 网站规则失效时：AI 自动诊断与修补 (CSS Repair)</span>
                    <span className="text-[10px] text-amber-400 font-mono">规则自愈</span>
                  </div>
                  <p className="text-[11px] text-zinc-400">
                    如果目标网站更新了前端样式导致以前写的 CSS 选择器抓不到内容，只需在【规则与插件】中点击【AI 智能修补】，大模型会自动分析新版 HTML 并生成替换规则。
                  </p>
                </div>

                <div className="p-3.5 bg-zinc-950 border border-zinc-800 rounded-lg space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-zinc-200">③ 定向自主研究智能体 (Research Agent)</span>
                    <span className="text-[10px] text-blue-400 font-mono">自主探查</span>
                  </div>
                  <p className="text-[11px] text-zinc-400">
                    在左侧【定向调研】输入想要探究的课题，AI 将自动拆解子话题、自主采集相关文档并综合生成一份 Markdown 调研报告。
                  </p>
                </div>

                <div className="p-3.5 bg-zinc-950 border border-zinc-800 rounded-lg space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-zinc-200">④ 怎么配置 AI 接口？</span>
                    <span className="text-[10px] text-emerald-400 font-mono">兼容 OpenAI 格式</span>
                  </div>
                  <p className="text-[11px] text-zinc-400">
                    点击左下角【系统设置】，填入 API Key 即可。支持 DeepSeek、OpenAI、SiliconFlow、Kimi，以及纯本地运行的 Ollama / vLLM（零公网暴露）。
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: FAQ */}
          {activeTab === "faq" && (
            <div className="space-y-4">
              <div className="p-3.5 bg-zinc-950 border border-zinc-800 rounded-lg space-y-1.5">
                <h4 className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
                  <span className="text-amber-400 font-bold">Q:</span>
                  我完全没用过爬虫，打开软件第一件事做什么？
                </h4>
                <p className="text-[11px] text-zinc-400 leading-relaxed pl-4">
                  先点击左侧【新建采集项目】，输入一个名字（比如“我的测试”）。进入项目后，点击右上角的【发起新采集】，在弹窗里直接点击【💡 填入测试示例】，然后点击底部【开始采集任务】。你就能亲眼看到软件是怎么把网页下载、清洗并转成 Markdown 的！
                </p>
              </div>

              <div className="p-3.5 bg-zinc-950 border border-zinc-800 rounded-lg space-y-1.5">
                <h4 className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
                  <span className="text-amber-400 font-bold">Q:</span>
                  抓取回来的网页正文是空的，或者只有两行字？
                </h4>
                <p className="text-[11px] text-zinc-400 leading-relaxed pl-4">
                  这是因为现代网站很多需要执行 JavaScript 代码（如 Vue/React 单页应用）。在采集向导中，将【网页抓取引擎】从默认的“Smart”切换为 <strong className="text-zinc-200">Browser 浏览器渲染</strong>，系统会自动调用 Chromium 浏览器内核把网页渲染完整后再提取。
                </p>
              </div>

              <div className="p-3.5 bg-zinc-950 border border-zinc-800 rounded-lg space-y-1.5">
                <h4 className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
                  <span className="text-amber-400 font-bold">Q:</span>
                  怎么只抓文章，不顺着链接爬到无关的外部广告网站？
                </h4>
                <p className="text-[11px] text-zinc-400 leading-relaxed pl-4">
                  在采集向导中，将【采集范围 (Scope)】选择为 <strong className="text-zinc-200">当前域名 (domain)</strong> 或 <strong className="text-zinc-200">当前目录及下级路径 (path)</strong>。爬虫引擎会自动过滤掉所有外链域名。
                </p>
              </div>

              <div className="p-3.5 bg-zinc-950 border border-zinc-800 rounded-lg space-y-1.5">
                <h4 className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
                  <span className="text-amber-400 font-bold">Q:</span>
                  抓取速度太快被网站拦截了怎么办？
                </h4>
                <p className="text-[11px] text-zinc-400 leading-relaxed pl-4">
                  在采集向导中将【频控策略预设】从“极速模式”切换为 <strong className="text-zinc-200">温和保护 (gentle)</strong>，系统会自动将同一域名的请求间隔拉长至 1500ms，并发限制为 3，最大程度避免对目标站点造成负担与被风控。
                </p>
              </div>

              <div className="p-3.5 bg-zinc-950 border border-zinc-800 rounded-lg space-y-1.5">
                <h4 className="text-xs font-semibold text-zinc-200 flex items-center gap-1.5">
                  <span className="text-amber-400 font-bold">Q:</span>
                  我的数据安全吗？会上传到任何云端吗？
                </h4>
                <p className="text-[11px] text-zinc-400 leading-relaxed pl-4">
                  绝对安全。软件所有爬取的原始 HTML、Markdown 和数据库（SQLite）全部保存在您的本地机器中。若不开启 AI 功能，软件绝不会向任何第三方服务器发送您的任何采集内容。
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-3 border-t border-zinc-800 bg-zinc-950 flex items-center justify-between shrink-0">
          <div className="text-[11px] text-zinc-500">
            随时可在左侧导航栏点击「使用教程」再次打开本指南
          </div>

          <div className="flex items-center gap-2.5">
            {onStartDemo && (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onStartDemo();
                }}
                className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-md shadow-sm transition-all flex items-center gap-1.5 active:scale-95"
              >
                <Play size={13} className="fill-white stroke-none" />
                <span>一键体验示例采集</span>
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-semibold rounded-md transition-colors"
            >
              我知道了，开始使用
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

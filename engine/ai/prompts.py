from typing import Dict, Any

PROMPT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "article_summary_v1": {
        "version": "v1.0",
        "system": "对输入的网页正文提取结构化内容摘要。输出要求：1. 核心要点（要点列表）；2. 主要观点与结论。语言简练客观，禁止添加前言客套，使用 Markdown 格式直接输出。",
        "user": "【文章标题】: {title}\n【文章正文】:\n{content}\n\n请生成摘要："
    },
    "article_tags_v1": {
        "version": "v1.0",
        "system": "根据正文内容提炼 3 到 6 个核心主题标签。严格输出标准 JSON 字符串数组，如：[\"标签1\", \"标签2\"]。禁止输出任何其他文字或标记。",
        "user": "【文章标题】: {title}\n【正文】:\n{content}"
    },
    "page_classification_v1": {
        "version": "v1.0",
        "system": "判断网页内容类型。可选分类：Article, List, Video, Documentation, Forum, Product, News, Other。严格返回 JSON 对象：{\"category\": \"Article\", \"confidence\": 0.95}，不输出其他内容。",
        "user": "【标题】: {title}\n【正文片段】:\n{content}"
    },
    "change_analysis_v1": {
        "version": "v1.0",
        "system": "对比同一网页新旧文本的实际差异，用 1~2 句话简述具体变更（如更新参数、新增章节、下架说明等）。保持中立客观，直接输出说明文字。",
        "user": "【旧版本】:\n{old_content}\n\n【新版本】:\n{new_content}\n\n变更总结："
    },
    "entity_extraction_v1": {
        "version": "v1.0",
        "system": "从文本中抽取关键实体，按类别归纳为：persons(人物), organizations(机构), products(产品/技术), locations(地点)。严格返回 JSON：{\"persons\": [...], \"organizations\": [...], \"products\": [...], \"locations\": [...]}，禁止输出解释文字。",
        "user": "【文章标题】: {title}\n【正文】:\n{content}"
    },
    "project_report_v1": {
        "version": "v1.0",
        "system": "根据已采纳的文档库摘要，整理一份客观、详实的综合研究分析报告。结构应包括：1. 概述与背景；2. 关键事实与要点归纳；3. 涉及的主要机构或产品；4. 总结与后续观察。使用标准 Markdown 格式排版，行文务实，禁止主观臆断与套话。",
        "user": "【项目名称】: {title}\n【参考文档库汇总】:\n{content}\n\n请生成分析报告："
    },
    "selector_repair_v1": {
        "version": "v1.0",
        "system": "分析网页 DOM 结构，修复失效的 CSS 选择器。对比原规则与新 DOM 骨架，找出定位准确且容错率高的 CSS 选择器。严格输出 JSON：{\"degraded_fields\": [...], \"suggested_rules\": {\"title\": \"...\", \"content\": \"...\", \"author\": \"...\", \"date\": \"...\"}, \"repair_reason\": \"...\", \"confidence\": 0.95}，不要包含代码块标记外的非 JSON 文本。",
        "user": "【原选择器规则】: {old_rules}\n【失效/退化字段】: {failed_fields}\n【当前改版后 DOM 骨架】:\n{dom_skeleton}\n\n请输出修复规则："
    },
    "research_decompose_v1": {
        "version": "v1.0",
        "system": "将指定的研究课题分解为 3~4 个具体的调研子问题，并为各子问题生成针对搜索引擎的高检索价值关键词。严格输出 JSON：{\"sub_topics\": [\"...\"], \"search_queries\": [\"...\"], \"focus_points\": [\"...\"]}，禁止多余输出。",
        "user": "【研究课题】: {topic}\n【背景/补充要求】: {content}\n\n请输出检索规划："
    },
    "relevance_scoring_v1": {
        "version": "v1.0",
        "system": "评估候选网页标题与内容片段是否与给定的研究主题相关。严格输出 JSON：{\"score\": 80, \"relevant\": true, \"reason\": \"涵盖相关技术参数与实现方案\"}，score 范围为 0 到 100，大于等于 60 视为 relevant=true。",
        "user": "【研究主题】: {topic}\n【候选网页标题】: {title}\n【网页片段】:\n{content}\n\n请评估相关度："
    },
    "knowledge_gap_v1": {
        "version": "v1.0",
        "system": "分析当前已收集的文献证据，评估对核心课题的信息覆盖度是否充分。严格输出 JSON：{\"is_sufficient\": false, \"missing_aspects\": [\"缺少实际测试数据\"], \"suggested_followups\": [\"检索性能评测对比\"], \"confidence\": 0.8}，禁止多余文本。",
        "user": "【研究主题】: {topic}\n【已收集证据摘要】:\n{content}\n\n请评估信息充分度："
    }
}

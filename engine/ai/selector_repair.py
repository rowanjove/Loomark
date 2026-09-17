import json
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from engine.ai.client import AIProviderClient
from engine.extractors.json_rule_adapter import JsonRuleExtractor

logger = logging.getLogger(__name__)

def prune_dom_for_repair(html: str, max_chars: int = 4000) -> str:
    """
    Prune high-noise elements (scripts, styles, SVGs, footers, navs)
    and retain essential semantic containers and hierarchy with tags, classes, and ids.
    Reduces token usage while focusing LLM attention on content wrappers.
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # Strip out non-content elements
    for el in soup(["script", "style", "svg", "noscript", "iframe", "footer", "nav", "header", "form"]):
        el.decompose()

    # Collect structural elements
    lines = []
    interesting_tags = ["h1", "h2", "h3", "article", "main", "section", "div", "p", "span", "time", "a"]
    for el in soup.find_all(interesting_tags):
        tag = el.name
        classes = ".".join(el.get("class", []))
        el_id = el.get("id")
        ident = tag
        if el_id:
            ident += f"#{el_id}"
        if classes:
            ident += f".{classes}"

        text = el.get_text().strip()
        # Truncate text snippet
        snippet = ""
        if text:
            clean_text = " ".join(text.split())
            snippet = f' "{clean_text[:40]}..."' if len(clean_text) > 40 else f' "{clean_text}"'

        lines.append(f"<{ident}>{snippet}")

    full_skeleton = "\n".join(lines)
    if len(full_skeleton) > max_chars:
        return full_skeleton[:max_chars] + "\n<!-- [DOM skeleton truncated] -->"
    return full_skeleton

def detect_selector_degradation(html: str, rules: Dict[str, str]) -> Dict[str, Any]:
    """
    Test CSS selectors against given HTML. If key fields (title, content)
    extract empty or very short snippets, flag as degraded.
    """
    extractor = JsonRuleExtractor(rules)
    res = extractor.extract(html, "https://preview.local")

    failed_fields = []
    if "title" in rules and (not res.title or res.title == "Untitled"):
        failed_fields.append("title")
    if "content" in rules and len(res.text.strip()) < 30:
        failed_fields.append("content")
    if "author" in rules and not res.author:
        failed_fields.append("author")
    if "date" in rules and not res.published_at:
        failed_fields.append("date")

    is_degraded = bool("content" in failed_fields or "title" in failed_fields)

    return {
        "is_degraded": is_degraded,
        "failed_fields": failed_fields,
        "current_extraction": {
            "title": res.title,
            "content": res.text[:200],
            "content_length": len(res.text),
            "author": res.author,
            "published_at": res.published_at
        }
    }

def preview_rule_extraction(html: str, rules: Dict[str, str]) -> Dict[str, Any]:
    """Execute rule extraction on given HTML for live preview comparison."""
    extractor = JsonRuleExtractor(rules)
    res = extractor.extract(html, "https://preview.local")
    return {
        "title": res.title,
        "content_snippet": res.text[:300],
        "content_length": len(res.text),
        "author": res.author,
        "published_at": res.published_at
    }

async def diagnose_and_repair_selectors(
    url: str,
    html: str,
    rules: Dict[str, str],
    ai_client: Optional[AIProviderClient]
) -> Dict[str, Any]:
    """
    Diagnose degraded selectors using DOM pruning and AI inference (PRD Section 30).
    Returns suggested repaired rules with preview of before/after extraction.
    """
    degrade_info = detect_selector_degradation(html, rules)
    skeleton = prune_dom_for_repair(html)

    if not ai_client:
        return {
            "success": False,
            "is_degraded": degrade_info["is_degraded"],
            "failed_fields": degrade_info["failed_fields"],
            "error": "未配置或未启用 AI 服务，无法进行智能诊断与选择器推导。"
        }

    # Prepare AI repair task
    extra_params = {
        "old_rules": json.dumps(rules, ensure_ascii=False),
        "failed_fields": ", ".join(degrade_info["failed_fields"]) or "未提取到有效数据",
        "dom_skeleton": skeleton
    }

    ai_res = await ai_client.execute_task(
        task_type="selector_repair_v1",
        content=skeleton,
        title=url,
        extra_params=extra_params
    )

    if "error" in ai_res:
        return {
            "success": False,
            "is_degraded": degrade_info["is_degraded"],
            "failed_fields": degrade_info["failed_fields"],
            "error": f"AI 诊断失败: {ai_res['error']}"
        }

    raw_data = ai_res["result"].get("text", "")
    suggested_rules = dict(rules)
    repair_reason = "AI 推导并重构了页面选择器"
    confidence = 0.85

    # Extract JSON from output
    try:
        clean_json = raw_data.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        parsed = json.loads(clean_json.strip())

        if "suggested_rules" in parsed and isinstance(parsed["suggested_rules"], dict):
            suggested_rules.update(parsed["suggested_rules"])
        if "repair_reason" in parsed:
            repair_reason = parsed["repair_reason"]
        if "confidence" in parsed:
            confidence = float(parsed["confidence"])
    except Exception as e:
        logger.warning(f"Failed to parse AI repair JSON response: {e}")

    # Sandbox test new rules on current HTML
    preview_before = degrade_info["current_extraction"]
    preview_after = preview_rule_extraction(html, suggested_rules)

    return {
        "success": True,
        "is_degraded": degrade_info["is_degraded"],
        "failed_fields": degrade_info["failed_fields"],
        "old_rules": rules,
        "suggested_rules": suggested_rules,
        "repair_reason": repair_reason,
        "confidence": confidence,
        "preview_before": preview_before,
        "preview_after": preview_after
    }

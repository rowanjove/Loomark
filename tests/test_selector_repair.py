import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from engine.ai.selector_repair import (
    prune_dom_for_repair,
    detect_selector_degradation,
    preview_rule_extraction,
    diagnose_and_repair_selectors
)
from engine.extractors.plugin_manager import PluginManager

SAMPLE_OLD_HTML = """
<html>
<body>
    <script>console.log("noisy tracking script");</script>
    <style>.css { color: red; }</style>
    <header><nav>Navigation links</nav></header>
    <div class="content-wrapper">
        <h1 class="post-title">Deep Learning in 2026</h1>
        <div class="byline">Dr. Alex</div>
        <div class="post-body">
            This is the original article body talking about AI crawlers and semantic reasoning engines.
            It has multiple detailed sentences explaining architecture and distributed design.
        </div>
    </div>
</body>
</html>
"""

SAMPLE_REDESIGNED_HTML = """
<html>
<body>
    <header>Site Header</header>
    <!-- Website redesigned: post-body changed to modern-article-text -->
    <main class="main-container">
        <h1 class="modern-heading">Deep Learning in 2026 (Updated)</h1>
        <span class="author-name">Dr. Alex</span>
        <article class="modern-article-text">
            This is the modern redesigned article body. It has been moved into an article tag with modern CSS classes.
            It provides thorough explanations of intelligent autonomous agents.
        </article>
    </main>
</body>
</html>
"""

def test_prune_dom_for_repair():
    pruned = prune_dom_for_repair(SAMPLE_OLD_HTML)
    assert "console.log" not in pruned
    assert "color: red" not in pruned
    assert "<h1.post-title>" in pruned or "h1" in pruned

def test_detect_selector_degradation():
    old_rules = {
        "title": "h1.post-title",
        "content": ".post-body",
        "author": ".byline"
    }
    # On old HTML: should NOT be degraded
    info_ok = detect_selector_degradation(SAMPLE_OLD_HTML, old_rules)
    assert info_ok["is_degraded"] is False

    # On redesigned HTML: old rules fail to match .post-body -> should be degraded
    info_degraded = detect_selector_degradation(SAMPLE_REDESIGNED_HTML, old_rules)
    assert info_degraded["is_degraded"] is True
    assert "content" in info_degraded["failed_fields"]

@pytest.mark.asyncio
async def test_diagnose_and_repair_selectors():
    old_rules = {
        "title": "h1.post-title",
        "content": ".post-body",
        "author": ".byline"
    }

    mock_ai = MagicMock()
    mock_ai.execute_task = AsyncMock(return_value={
        "task_type": "selector_repair_v1",
        "result": {
            "text": json.dumps({
                "degraded_fields": ["content", "title"],
                "suggested_rules": {
                    "title": "h1.modern-heading",
                    "content": "article.modern-article-text",
                    "author": "span.author-name"
                },
                "repair_reason": "页面改版为现代语义化标签",
                "confidence": 0.96
            })
        }
    })

    res = await diagnose_and_repair_selectors(
        url="https://example.com/blog/1",
        html=SAMPLE_REDESIGNED_HTML,
        rules=old_rules,
        ai_client=mock_ai
    )

    assert res["success"] is True
    assert res["is_degraded"] is True
    assert res["suggested_rules"]["content"] == "article.modern-article-text"
    assert "redesigned article body" in res["preview_after"]["content_snippet"]

def test_plugin_manager_apply_repair(tmp_path):
    pm = PluginManager(plugins_dir=tmp_path)
    created = pm.create_or_update_rule_plugin({
        "id": "auto_repair_target",
        "name": "Target Plugin",
        "match": ["target.com"],
        "rules": {"title": "h1", "content": ".old-body"}
    })
    assert created["rules"]["content"] == ".old-body"

    # Apply repair
    updated = pm.apply_selector_repair("auto_repair_target", {
        "title": "h1.new",
        "content": ".new-body"
    })
    assert updated["rules"]["content"] == ".new-body"

    # Verify disk
    with open(tmp_path / "auto_repair_target" / "manifest.json", "r", encoding="utf-8") as f:
        disk_data = json.load(f)
    assert disk_data["rules"]["content"] == ".new-body"

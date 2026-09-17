import json
from typing import List, Dict, Any, Optional

PRESET_PLUGINS: List[Dict[str, Any]] = [
    {
        "id": "preset_weixin_article",
        "name": "微信公众号文章精粹",
        "version": "1.0.0",
        "description": "针对 mp.weixin.qq.com 微信公众平台深度优化的正文、作者与发布时间精准抽取适配器",
        "author": "Loomark Official",
        "match": ["mp.weixin.qq.com"],
        "category": ["article"],
        "capabilities": {"discover": True, "article": True, "subtitle": False, "comments": False},
        "permissions": ["network"],
        "rules": {
            "title": "#activity-name, .rich_media_title, h1",
            "content": "#js_content, .rich_media_content",
            "author": "#js_name, .rich_media_meta_text, .profile_nickname",
            "date": "#publish_time, em#post-date, .rich_media_meta_text"
        }
    },
    {
        "id": "preset_zhihu_column",
        "name": "知乎专栏与精选回答",
        "version": "1.0.0",
        "description": "针对知乎文章与回答页面的精准解析，支持公式、排版去噪与作者信息提取",
        "author": "Loomark Official",
        "match": ["zhuanlan.zhihu.com", "*.zhihu.com"],
        "category": ["article"],
        "capabilities": {"discover": True, "article": True, "subtitle": False, "comments": False},
        "permissions": ["network"],
        "rules": {
            "title": "h1.Post-Title, h1.QuestionHeader-title",
            "content": ".Post-RichText, .RichContent-inner, .AnswerCard",
            "author": ".AuthorInfo-name, .UserLink-link",
            "date": "time, .ContentItem-time"
        }
    },
    {
        "id": "preset_github_readme",
        "name": "GitHub 仓库与 Markdown 文档",
        "version": "1.0.0",
        "description": "提取 GitHub 仓库 README、Release 说明及 Wiki 技术文档",
        "author": "Loomark Official",
        "match": ["github.com"],
        "category": ["documentation"],
        "capabilities": {"discover": True, "article": True, "subtitle": False, "comments": False},
        "permissions": ["network"],
        "rules": {
            "title": "h1.entry-title, #readme h2, h1",
            "content": "article.markdown-body, #readme",
            "author": ".author, [rel='author']",
            "date": "relative-time, time"
        }
    },
    {
        "id": "preset_36kr_news",
        "name": "36Kr 科技商业快讯",
        "version": "1.0.0",
        "description": "针对 36氪 前沿商业、科技快讯与深度特稿的结构化解析器",
        "author": "Loomark Official",
        "match": ["*.36kr.com", "36kr.com"],
        "category": ["article"],
        "capabilities": {"discover": True, "article": True, "subtitle": False, "comments": False},
        "permissions": ["network"],
        "rules": {
            "title": "h1.article-title, .title-wrapper h1",
            "content": ".articleDetailContent, .common-width.content",
            "author": ".author-name, .author-info",
            "date": ".time, .item-time"
        }
    },
    {
        "id": "preset_juejin_post",
        "name": "掘金技术社区专栏",
        "version": "1.0.0",
        "description": "针对稀土掘金技术博客正文、代码高亮块与标签的专业提取",
        "author": "Loomark Official",
        "match": ["juejin.cn"],
        "category": ["article", "documentation"],
        "capabilities": {"discover": True, "article": True, "subtitle": False, "comments": False},
        "permissions": ["network"],
        "rules": {
            "title": "h1.article-title",
            "content": ".markdown-body, .article-content",
            "author": ".author-name .name, .username",
            "date": "time.time, .meta-box time"
        }
    },
    {
        "id": "preset_wikipedia_article",
        "name": "维基百科词条",
        "version": "1.0.0",
        "description": "针对维基百科词条的完整知识萃取，自动清洗导航栏与参考引用注脚",
        "author": "Loomark Official",
        "match": ["*.wikipedia.org", "wikipedia.org"],
        "category": ["documentation"],
        "capabilities": {"discover": True, "article": True, "subtitle": False, "comments": False},
        "permissions": ["network"],
        "rules": {
            "title": "#firstHeading, h1",
            "content": "#mw-content-text .mw-parser-output",
            "author": ".history-user, .mw-contributor",
            "date": "#footer-info-lastmod"
        }
    }
]

def get_preset_plugins() -> List[Dict[str, Any]]:
    """Return all bundled preset plugins."""
    return PRESET_PLUGINS

def validate_and_parse_plugin_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate imported plugin structure against PRD Section 25 & 82 Manifest Specification.
    """
    if not isinstance(data, dict):
        raise ValueError("插件文件格式必须为合法 JSON 字典对象")

    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("插件必须包含名称 'name'")

    match = data.get("match", [])
    if isinstance(match, str):
        match = [match.strip()]
    if not isinstance(match, list) or len(match) == 0:
        raise ValueError("插件必须包含至少一个匹配域名 'match'")

    rules = data.get("rules", {})
    if not isinstance(rules, dict):
        raise ValueError("插件规则 'rules' 必须为字典对象")

    manifest = {
        "name": name,
        "version": data.get("version", "1.0.0"),
        "description": data.get("description", ""),
        "author": data.get("author", "Community Contributor"),
        "match": match,
        "category": data.get("category", ["article"]),
        "capabilities": data.get("capabilities", {"discover": True, "article": True}),
        "permissions": data.get("permissions", ["network"]),
        "rules": {
            "title": rules.get("title", "h1"),
            "content": rules.get("content", "article, .content"),
            "author": rules.get("author", ".author"),
            "date": rules.get("date", "time")
        }
    }
    return manifest

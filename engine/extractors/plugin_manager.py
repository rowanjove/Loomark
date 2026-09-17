import os
import json
import fnmatch
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from engine.config import PLUGINS_DIR
from engine.db.session import get_db
from engine.extractors.generic_article import GenericArticleExtractor
from engine.extractors.generic_website import GenericWebsiteExtractor
from engine.extractors.json_rule_adapter import JsonRuleExtractor
from engine.extractors.media_subtitle import MediaSubtitleExtractor

logger = logging.getLogger(__name__)

BUILTIN_PLUGINS = [
    {
        "id": "generic_article",
        "name": "Generic Article Adapter",
        "version": "1.0.0",
        "type": "builtin",
        "author": "Loomark Core",
        "match": ["*"],
        "category": ["article"],
        "description": "基于 Trafilatura 的通用博客与新闻文章抽取器，自动提取标题、正文、作者与发布时间",
        "is_builtin": True,
        "enabled": True,
        "capabilities": {"article": True, "links": True, "metadata": True}
    },
    {
        "id": "generic_website",
        "name": "Generic Website Adapter",
        "version": "1.0.0",
        "type": "builtin",
        "author": "Loomark Core",
        "match": ["*"],
        "category": ["website"],
        "description": "未知网站默认兜底适配器，负责递归外链发现、Meta 描述提取与 Sitemap 探测",
        "is_builtin": True,
        "enabled": True,
        "capabilities": {"discover": True, "metadata": True}
    },
    {
        "id": "video_subtitle",
        "name": "Media & Subtitle Pipeline",
        "version": "1.0.0",
        "type": "media",
        "author": "Loomark Core",
        "match": ["*youtube.com*", "*youtu.be*", "*bilibili.com*"],
        "category": ["video"],
        "description": "基于 yt-dlp 的视频元数据与自动字幕时间轴抽取器，生成结构化字幕切片",
        "is_builtin": True,
        "enabled": True,
        "capabilities": {"subtitle": True, "media": True}
    }
]

class PluginManager:
    """
    Manages custom Site Adapters, JSON Rule plugins, and Built-in extractors
    (PRD Sections 24-28, 81-82, 103).
    """
    def __init__(self, plugins_dir: Path = PLUGINS_DIR):
        self.plugins_dir = plugins_dir
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self._cached_plugins: Optional[List[Dict[str, Any]]] = None

    def invalidate_cache(self):
        """Invalidate the in-memory plugins cache on mutations."""
        self._cached_plugins = None

    def list_plugins(self, force_reload: bool = False) -> List[Dict[str, Any]]:
        """List all plugins (built-ins + disk-loaded plugins) with in-memory caching."""
        if self._cached_plugins is not None and not force_reload:
            return self._cached_plugins

        all_plugins = [dict(p) for p in BUILTIN_PLUGINS]

        # Scan plugins directory for manifest.json
        for item in self.plugins_dir.iterdir():
            if item.is_dir():
                manifest_file = item / "manifest.json"
                if manifest_file.exists():
                    try:
                        with open(manifest_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            data["is_builtin"] = False
                            all_plugins.append(data)
                    except Exception as e:
                        logger.warning(f"Failed to read plugin manifest in {item}: {e}")

        # Sync/override enabled state with database if available
        try:
            with get_db() as conn:
                rows = conn.execute("SELECT id, enabled FROM plugins;").fetchall()
                db_states = {r["id"]: bool(r["enabled"]) for r in rows}
                for p in all_plugins:
                    if p["id"] in db_states:
                        p["enabled"] = db_states[p["id"]]
        except Exception:
            pass

        self._cached_plugins = all_plugins
        return all_plugins

    def get_plugin(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get plugin by ID from cached/loaded plugins."""
        for p in self.list_plugins():
            if p.get("id") == plugin_id:
                return p
        return None

    def create_or_update_rule_plugin(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or save a JSON Rule plugin on disk and in database."""
        raw_id = data.get("id") or data.get("name", "custom_rule").lower().replace(" ", "_")
        # Sanitize id: enforce safe ASCII alphanumeric characters
        plugin_id = "".join(c for c in raw_id if (c.isascii() and c.isalnum()) or c in ("-", "_")).strip("-_")
        if not plugin_id:
            import uuid
            plugin_id = f"rule_{uuid.uuid4().hex[:8]}"

        plugin_dir = (self.plugins_dir / plugin_id).resolve()
        if plugin_dir == self.plugins_dir.resolve() or self.plugins_dir.resolve() not in plugin_dir.parents:
            raise ValueError(f"Invalid or unsafe plugin ID: {plugin_id}")

        plugin_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "id": plugin_id,
            "name": data.get("name", plugin_id),
            "version": data.get("version", "1.0.0"),
            "author": data.get("author", "User"),
            "type": "rule",
            "match": data.get("match") if isinstance(data.get("match"), list) else [data.get("match", "*")],
            "category": data.get("category", ["article"]),
            "description": data.get("description", ""),
            "rules": data.get("rules", {}),
            "enabled": bool(data.get("enabled", True)),
            "is_builtin": False
        }

        manifest_file = plugin_dir / "manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        # Upsert into database
        try:
            with get_db() as conn:
                conn.execute(
                    """
                    INSERT INTO plugins (id, name, version, type, manifest_json, is_builtin, enabled)
                    VALUES (?, ?, ?, 'rule', ?, 0, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        version = excluded.version,
                        manifest_json = excluded.manifest_json,
                        enabled = excluded.enabled;
                    """,
                    (plugin_id, manifest["name"], manifest["version"], json.dumps(manifest), 1 if manifest["enabled"] else 0)
                )
        except Exception as e:
            logger.warning(f"Database plugin record save warning: {e}")

        self.invalidate_cache()
        return manifest

    def toggle_plugin(self, plugin_id: str, enabled: bool) -> bool:
        """Enable or disable a plugin."""
        # Builtin toggle in DB
        try:
            with get_db() as conn:
                conn.execute(
                    """
                    INSERT INTO plugins (id, name, version, type, manifest_json, is_builtin, enabled)
                    VALUES (?, ?, '1.0.0', 'builtin', '{}', 1, ?)
                    ON CONFLICT(id) DO UPDATE SET enabled = excluded.enabled;
                    """,
                    (plugin_id, plugin_id, 1 if enabled else 0)
                )
        except Exception:
            pass

        # If disk plugin, update manifest
        manifest_file = self.plugins_dir / plugin_id / "manifest.json"
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["enabled"] = enabled
                with open(manifest_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        self.invalidate_cache()
        return True

    def delete_plugin(self, plugin_id: str) -> bool:
        """Delete a custom user plugin."""
        if not plugin_id or not plugin_id.strip():
            raise ValueError("Plugin ID cannot be empty.")

        if any(b["id"] == plugin_id for b in BUILTIN_PLUGINS):
            raise ValueError("Cannot delete built-in core plugins.")

        import shutil
        plugin_dir = (self.plugins_dir / plugin_id).resolve()
        if plugin_dir == self.plugins_dir.resolve() or self.plugins_dir.resolve() not in plugin_dir.parents:
            raise ValueError(f"Security error: Attempted unsafe plugin directory deletion: {plugin_dir}")

        if plugin_dir.exists():
            shutil.rmtree(plugin_dir, ignore_errors=True)

        try:
            with get_db() as conn:
                conn.execute("DELETE FROM plugins WHERE id = ?;", (plugin_id,))
        except Exception:
            pass
        self.invalidate_cache()
        return True

    def find_matching_extractor(self, url: str) -> Optional[Any]:
        """
        Two-tier Adapter resolution (PRD Section 27):
        Check custom active site plugins first; if match domain, return JsonRuleExtractor.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        plugins = self.list_plugins()
        for p in plugins:
            if not p.get("enabled", True):
                continue
            if p.get("type") == "rule" and p.get("rules"):
                matches = p.get("match", [])
                for pattern in matches:
                    pattern_clean = pattern.lower().replace("https://", "").replace("http://", "").strip("/")
                    if fnmatch.fnmatch(domain, pattern_clean) or pattern_clean in domain:
                        return JsonRuleExtractor(p["rules"])
        return None

    async def test_rule_online(self, url: str, rules: Dict[str, str], html: Optional[str] = None) -> Dict[str, Any]:
        """
        Test JSON rule extraction against target URL or provided HTML string (PRD Section 29-30).
        """
        if not html:
            from engine.fetcher.http_fetcher import HttpFetcher
            fetcher = HttpFetcher(timeout_seconds=12)
            try:
                res = await fetcher.fetch(url)
                if res.status_code == 0 or not res.text:
                    return {"success": False, "error": res.error or f"Failed to fetch {url}"}
                html = res.text
            finally:
                await fetcher.close()

        extractor = JsonRuleExtractor(rules)
        extracted = extractor.extract(html, url)
        return {
            "success": True,
            "url": url,
            "title": extracted.title,
            "author": extracted.author,
            "published_at": extracted.published_at,
            "text_preview": (extracted.text or "")[:400],
            "text_length": len(extracted.text or ""),
            "markdown_preview": (extracted.markdown or "")[:400],
            "links_sample": extracted.links[:10],
            "total_links": len(extracted.links)
        }

    def apply_selector_repair(self, plugin_id: str, suggested_rules: Dict[str, str]) -> Dict[str, Any]:
        """Apply repaired CSS selectors to a custom rule plugin (PRD Section 30)."""
        manifest_file = self.plugins_dir / plugin_id / "manifest.json"
        if not manifest_file.exists():
            raise ValueError(f"Plugin '{plugin_id}' not found on disk.")

        with open(manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["rules"] = suggested_rules
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Update database
        try:
            with get_db() as conn:
                conn.execute(
                    "UPDATE plugins SET manifest_json = ? WHERE id = ?;",
                    (json.dumps(data), plugin_id)
                )
        except Exception as e:
            logger.warning(f"Database plugin update failed: {e}")

        self.invalidate_cache()
        return data

# Global singleton
plugin_manager = PluginManager()

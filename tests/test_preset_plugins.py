import pytest
from engine.extractors.preset_plugins import get_preset_plugins, validate_and_parse_plugin_data
from engine.extractors.plugin_manager import PluginManager

def test_preset_plugins_list():
    presets = get_preset_plugins()
    assert len(presets) >= 5
    ids = [p["id"] for p in presets]
    assert "preset_weixin_article" in ids
    assert "preset_zhihu_column" in ids
    assert "preset_github_readme" in ids
    assert "preset_36kr_news" in ids

    for p in presets:
        assert p["name"]
        assert len(p["match"]) > 0
        assert "rules" in p
        assert "title" in p["rules"]
        assert "permissions" in p

def test_validate_and_parse_plugin_data():
    valid_payload = {
        "name": "Custom Test Site",
        "match": ["*.test.com"],
        "rules": {
            "title": "h1.title",
            "content": ".content"
        }
    }
    manifest = validate_and_parse_plugin_data(valid_payload)
    assert manifest["name"] == "Custom Test Site"
    assert manifest["match"] == ["*.test.com"]
    assert manifest["rules"]["title"] == "h1.title"

    # Missing name should error
    with pytest.raises(ValueError):
        validate_and_parse_plugin_data({"match": ["*.test.com"]})

    # Missing match should error
    with pytest.raises(ValueError):
        validate_and_parse_plugin_data({"name": "Test Site", "match": []})

def test_install_preset_plugin(tmp_path):
    mgr = PluginManager(plugins_dir=tmp_path / "plugins")
    presets = get_preset_plugins()
    weixin = next(p for p in presets if p["id"] == "preset_weixin_article")

    installed = mgr.create_or_update_rule_plugin(weixin)
    assert installed["id"] == "preset_weixin_article"
    assert installed["enabled"] is True

    # List plugins from manager
    all_plugins = mgr.list_plugins()
    installed_ids = [p["id"] for p in all_plugins]
    assert "preset_weixin_article" in installed_ids

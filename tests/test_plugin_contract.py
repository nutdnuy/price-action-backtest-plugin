from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_plugin_files_exist():
    required = [
        ".codex-plugin/plugin.json",
        ".agents/plugins/marketplace.json",
        ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
        "README.md",
        "LICENSE",
        "pyproject.toml",
        ".gitignore",
        "skills/price-action-backtest/SKILL.md",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert missing == []


def test_codex_manifest_names_skill_directory():
    manifest = (ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
    assert '"name": "price-action-backtest-plugin"' in manifest
    assert '"skills": "./skills/"' in manifest
    assert '"Data & Analytics"' in manifest


def test_claude_manifest_names_skill_directory():
    manifest = (ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
    assert '"name": "price-action-backtest-plugin"' in manifest
    assert '"./skills/price-action-backtest"' in manifest

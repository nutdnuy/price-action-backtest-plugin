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


def test_skill_has_required_workflow_and_safety_language():
    skill = (ROOT / "skills/price-action-backtest/SKILL.md").read_text(encoding="utf-8")
    assert "OHLCV" in skill
    assert "lookahead" in skill.lower()
    assert "not trading instructions" in skill
    assert "python3 scripts/price_action_backtest.py" in skill


def test_task2_docs_clarify_readiness_and_signal_timing():
    skill = (ROOT / "skills/price-action-backtest/SKILL.md").read_text(encoding="utf-8")
    command_paths = [
        "commands/backtest-setup.md",
        "commands/backtest-webull-fetch.md",
        "commands/backtest-init-run.md",
        "commands/backtest-run.md",
        "commands/backtest-report.md",
        "commands/backtest-audit.md",
    ]
    workflow = (
        ROOT / "skills/price-action-backtest/references/workflow.md"
    ).read_text(encoding="utf-8")
    limitations = (
        ROOT / "skills/price-action-backtest/references/limitations.md"
    ).read_text(encoding="utf-8")

    assert "intended V1 workflow" in skill
    for path in command_paths:
        command_doc = (ROOT / path).read_text(encoding="utf-8")
        assert "intended V1 workflow" in command_doc
    assert "position[t+1] = signal[t]" in workflow
    assert "position[t+1] = signal[t]" in limitations
    assert "signal at close t applies only to the next bar's return" in workflow
    assert "signal at close t applies only to the next bar's return" in limitations


def test_skill_documents_webull_read_only_import():
    skill = (ROOT / "skills/price-action-backtest/SKILL.md").read_text(encoding="utf-8")
    workflow = (
        ROOT / "skills/price-action-backtest/references/workflow.md"
    ).read_text(encoding="utf-8")
    limitations = (
        ROOT / "skills/price-action-backtest/references/limitations.md"
    ).read_text(encoding="utf-8")
    command = (ROOT / "commands/backtest-webull-fetch.md").read_text(encoding="utf-8")

    for text in [skill, workflow, limitations, command]:
        assert "Webull" in text
        assert "read-only" in text
    assert "webull-fetch-bars" in command
    assert "data/private" in command
    assert "WEBULL_APP_SECRET" in command
    assert "place orders" in skill


def test_workflow_documents_optional_volume_contract():
    workflow = (
        ROOT / "skills/price-action-backtest/references/workflow.md"
    ).read_text(encoding="utf-8")
    workflow_lower = workflow.lower()

    for column in ["date", "open", "high", "low", "close"]:
        assert column in workflow_lower
    assert "required columns" in workflow_lower
    assert "volume" in workflow_lower
    assert "optional" in workflow_lower

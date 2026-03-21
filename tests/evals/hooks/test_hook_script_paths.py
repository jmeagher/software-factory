"""Tests verifying that all hook scripts referenced in hooks.json actually exist on disk.

These tests are deterministic (no LLM required). They parse hooks.json, resolve
the ${CLAUDE_PLUGIN_ROOT} variable, and assert that each referenced script file
exists and is executable.
"""
import json
import os
import stat
from pathlib import Path

import pytest

REPO_ROOT = Path("/home/jmeagher/devel/software-factory")
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"

# The plugin root where hook scripts are installed.
PLUGIN_ROOT = Path("/home/jmeagher/.claude/plugins/cache/jsf/jsf/0.1.0")


def _resolve_command(command: str) -> Path:
    """Resolve ${CLAUDE_PLUGIN_ROOT} in a command string to an absolute path."""
    resolved = command.replace("${CLAUDE_PLUGIN_ROOT}", str(PLUGIN_ROOT))
    # Extract the script path (first token, since the command is the script itself)
    script_path = resolved.split()[0]
    return Path(script_path)


def _collect_all_hook_commands(hooks_data: dict):
    """Yield (event, command_str) tuples for all hook entries that have a 'command'."""
    for event_name, entries in hooks_data.get("hooks", {}).items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                cmd = hook.get("command", "")
                if cmd:
                    yield event_name, cmd


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def hooks_data():
    assert HOOKS_JSON.exists(), f"hooks.json not found at {HOOKS_JSON}"
    return json.loads(HOOKS_JSON.read_text())


@pytest.fixture(scope="module")
def bash_hook_commands(hooks_data):
    """Return list of command strings from Bash PreToolUse hooks."""
    commands = []
    for entry in hooks_data.get("hooks", {}).get("PreToolUse", []):
        if entry.get("matcher") == "Bash":
            for hook in entry.get("hooks", []):
                if "command" in hook:
                    commands.append(hook["command"])
    return commands


# ---------------------------------------------------------------------------
# Tests: hooks.json references exactly the expected scripts
# ---------------------------------------------------------------------------


def test_bash_pretooluse_references_dangerous_bash(bash_hook_commands):
    names = [Path(c.split()[0]).name for c in bash_hook_commands]
    assert "block-dangerous-bash.sh" in names


def test_bash_pretooluse_references_dangerous_git(bash_hook_commands):
    names = [Path(c.split()[0]).name for c in bash_hook_commands]
    assert "block-dangerous-git.sh" in names


def test_bash_pretooluse_references_dangerous_sql(bash_hook_commands):
    names = [Path(c.split()[0]).name for c in bash_hook_commands]
    assert "block-dangerous-sql.sh" in names


# ---------------------------------------------------------------------------
# Tests: referenced scripts exist on disk at plugin root
# ---------------------------------------------------------------------------


def test_block_dangerous_bash_script_exists():
    p = PLUGIN_ROOT / "hooks" / "scripts" / "block-dangerous-bash.sh"
    assert p.exists(), f"Script not found: {p}"


def test_block_dangerous_git_script_exists():
    p = PLUGIN_ROOT / "hooks" / "scripts" / "block-dangerous-git.sh"
    assert p.exists(), f"Script not found: {p}"


def test_block_dangerous_sql_script_exists():
    p = PLUGIN_ROOT / "hooks" / "scripts" / "block-dangerous-sql.sh"
    assert p.exists(), f"Script not found: {p}"


def test_all_plugin_root_bash_scripts_exist(bash_hook_commands):
    """Every command in the Bash PreToolUse hooks must resolve to an existing file."""
    for cmd in bash_hook_commands:
        if "${CLAUDE_PLUGIN_ROOT}" in cmd:
            resolved = _resolve_command(cmd)
            assert resolved.exists(), f"Referenced script does not exist: {resolved} (from command: {cmd})"


# ---------------------------------------------------------------------------
# Tests: referenced scripts are executable
# ---------------------------------------------------------------------------


def test_block_dangerous_bash_script_is_executable():
    p = PLUGIN_ROOT / "hooks" / "scripts" / "block-dangerous-bash.sh"
    assert p.exists(), f"Script not found: {p}"
    assert os.access(p, os.X_OK), f"Script is not executable: {p}"


def test_block_dangerous_git_script_is_executable():
    p = PLUGIN_ROOT / "hooks" / "scripts" / "block-dangerous-git.sh"
    assert p.exists(), f"Script not found: {p}"
    assert os.access(p, os.X_OK), f"Script is not executable: {p}"


def test_block_dangerous_sql_script_is_executable():
    p = PLUGIN_ROOT / "hooks" / "scripts" / "block-dangerous-sql.sh"
    assert p.exists(), f"Script not found: {p}"
    assert os.access(p, os.X_OK), f"Script is not executable: {p}"


def test_all_plugin_root_bash_scripts_are_executable(bash_hook_commands):
    """Every command in the Bash PreToolUse hooks must be executable."""
    for cmd in bash_hook_commands:
        if "${CLAUDE_PLUGIN_ROOT}" in cmd:
            resolved = _resolve_command(cmd)
            if resolved.exists():
                assert os.access(resolved, os.X_OK), (
                    f"Script exists but is not executable: {resolved}"
                )


# ---------------------------------------------------------------------------
# Tests: scripts have correct shebang
# ---------------------------------------------------------------------------


def test_block_dangerous_bash_has_shebang():
    p = PLUGIN_ROOT / "hooks" / "scripts" / "block-dangerous-bash.sh"
    content = p.read_text()
    assert content.startswith("#!/"), f"Script missing shebang: {p}"


def test_block_dangerous_git_has_shebang():
    p = PLUGIN_ROOT / "hooks" / "scripts" / "block-dangerous-git.sh"
    content = p.read_text()
    assert content.startswith("#!/"), f"Script missing shebang: {p}"


def test_block_dangerous_sql_has_shebang():
    p = PLUGIN_ROOT / "hooks" / "scripts" / "block-dangerous-sql.sh"
    content = p.read_text()
    assert content.startswith("#!/"), f"Script missing shebang: {p}"


# ---------------------------------------------------------------------------
# Tests: repo-local scripts also exist (used by shell tests)
# ---------------------------------------------------------------------------


def test_local_block_dangerous_bash_exists():
    p = REPO_ROOT / "hooks" / "scripts" / "block-dangerous-bash.sh"
    assert p.exists(), f"Local script not found: {p}"


def test_local_block_dangerous_git_exists():
    p = REPO_ROOT / "hooks" / "scripts" / "block-dangerous-git.sh"
    assert p.exists(), f"Local script not found: {p}"


def test_local_block_dangerous_sql_exists():
    p = REPO_ROOT / "hooks" / "scripts" / "block-dangerous-sql.sh"
    assert p.exists(), f"Local script not found: {p}"


# ---------------------------------------------------------------------------
# Tests: no dead script references in hooks.json (all-in-one check)
# ---------------------------------------------------------------------------


def test_no_dead_script_references_in_hooks_json(hooks_data):
    """All ${CLAUDE_PLUGIN_ROOT}-based script references in hooks.json must exist."""
    missing = []
    for event, cmd in _collect_all_hook_commands(hooks_data):
        if "${CLAUDE_PLUGIN_ROOT}" in cmd and cmd.strip().endswith(".sh"):
            resolved = _resolve_command(cmd)
            if not resolved.exists():
                missing.append(f"{event}: {cmd} -> {resolved}")
    assert not missing, "Dead script references found:\n" + "\n".join(missing)

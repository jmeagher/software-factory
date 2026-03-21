"""Tests validating the structure of hooks.json in the JSF plugin.

These tests are deterministic (no LLM required) and run against the local
hooks.json in the repository root.
"""
import json
from pathlib import Path

import pytest

REPO_ROOT = Path("/home/jmeagher/devel/software-factory")
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def hooks_data():
    """Load and return the parsed hooks.json content."""
    assert HOOKS_JSON.exists(), f"hooks.json not found at {HOOKS_JSON}"
    return json.loads(HOOKS_JSON.read_text())


# ---------------------------------------------------------------------------
# Top-level structure
# ---------------------------------------------------------------------------


def test_hooks_json_exists():
    assert HOOKS_JSON.exists(), f"hooks.json not found at {HOOKS_JSON}"


def test_hooks_json_is_valid_json():
    content = HOOKS_JSON.read_text()
    data = json.loads(content)
    assert isinstance(data, dict)


def test_hooks_json_has_hooks_key(hooks_data):
    assert "hooks" in hooks_data, "hooks.json must have a top-level 'hooks' key"


def test_hooks_top_level_value_is_dict(hooks_data):
    assert isinstance(hooks_data["hooks"], dict), "'hooks' value must be a dict"


# ---------------------------------------------------------------------------
# PreToolUse section
# ---------------------------------------------------------------------------


def test_hooks_has_pretooluse(hooks_data):
    assert "PreToolUse" in hooks_data["hooks"], "hooks.json must have a 'PreToolUse' section"


def test_pretooluse_is_list(hooks_data):
    assert isinstance(hooks_data["hooks"]["PreToolUse"], list)


def test_pretooluse_is_nonempty(hooks_data):
    assert len(hooks_data["hooks"]["PreToolUse"]) > 0


def test_pretooluse_entries_have_hooks_key(hooks_data):
    for entry in hooks_data["hooks"]["PreToolUse"]:
        assert "hooks" in entry, f"PreToolUse entry missing 'hooks' key: {entry}"


def test_pretooluse_entries_hooks_is_list(hooks_data):
    for entry in hooks_data["hooks"]["PreToolUse"]:
        assert isinstance(entry["hooks"], list), f"'hooks' must be a list in entry: {entry}"


def test_pretooluse_each_hook_has_type(hooks_data):
    for entry in hooks_data["hooks"]["PreToolUse"]:
        for hook in entry["hooks"]:
            assert "type" in hook, f"hook entry missing 'type' field: {hook}"


def test_pretooluse_each_hook_has_command(hooks_data):
    for entry in hooks_data["hooks"]["PreToolUse"]:
        for hook in entry["hooks"]:
            assert "command" in hook, f"hook entry missing 'command' field: {hook}"


def test_pretooluse_each_hook_type_is_command(hooks_data):
    for entry in hooks_data["hooks"]["PreToolUse"]:
        for hook in entry["hooks"]:
            assert hook["type"] == "command", f"Expected type 'command', got '{hook['type']}'"


def test_pretooluse_each_hook_command_is_string(hooks_data):
    for entry in hooks_data["hooks"]["PreToolUse"]:
        for hook in entry["hooks"]:
            assert isinstance(hook["command"], str), f"'command' must be a string in hook: {hook}"


def test_pretooluse_each_hook_command_nonempty(hooks_data):
    for entry in hooks_data["hooks"]["PreToolUse"]:
        for hook in entry["hooks"]:
            assert hook["command"].strip(), f"'command' must not be empty in hook: {hook}"


def test_pretooluse_bash_matcher_entry_exists(hooks_data):
    """At least one PreToolUse entry should have matcher='Bash'."""
    matchers = [
        entry.get("matcher") for entry in hooks_data["hooks"]["PreToolUse"]
    ]
    assert "Bash" in matchers, "No PreToolUse entry with matcher='Bash' found"


def test_pretooluse_bash_hooks_count(hooks_data):
    """The Bash matcher entry should have exactly 3 hook scripts."""
    for entry in hooks_data["hooks"]["PreToolUse"]:
        if entry.get("matcher") == "Bash":
            assert len(entry["hooks"]) == 3, (
                f"Expected 3 Bash hooks, found {len(entry['hooks'])}"
            )


def test_pretooluse_bash_hooks_reference_expected_scripts(hooks_data):
    """The Bash matcher hooks should reference the three expected scripts."""
    expected_scripts = {
        "block-dangerous-bash.sh",
        "block-dangerous-git.sh",
        "block-dangerous-sql.sh",
    }
    for entry in hooks_data["hooks"]["PreToolUse"]:
        if entry.get("matcher") == "Bash":
            found = {
                Path(h["command"]).name for h in entry["hooks"]
            }
            assert found == expected_scripts, (
                f"Bash hooks reference unexpected scripts. Expected: {expected_scripts}, got: {found}"
            )


# ---------------------------------------------------------------------------
# SessionStart section (optional, but if present must be valid)
# ---------------------------------------------------------------------------


def test_session_start_if_present_is_list(hooks_data):
    if "SessionStart" in hooks_data["hooks"]:
        assert isinstance(hooks_data["hooks"]["SessionStart"], list)


def test_session_start_if_present_entries_have_hooks(hooks_data):
    if "SessionStart" in hooks_data["hooks"]:
        for entry in hooks_data["hooks"]["SessionStart"]:
            assert "hooks" in entry, f"SessionStart entry missing 'hooks' key: {entry}"


def test_session_start_if_present_hooks_have_type(hooks_data):
    if "SessionStart" in hooks_data["hooks"]:
        for entry in hooks_data["hooks"]["SessionStart"]:
            for hook in entry["hooks"]:
                assert "type" in hook, f"SessionStart hook missing 'type': {hook}"


def test_session_start_if_present_hooks_have_command(hooks_data):
    if "SessionStart" in hooks_data["hooks"]:
        for entry in hooks_data["hooks"]["SessionStart"]:
            for hook in entry["hooks"]:
                assert "command" in hook, f"SessionStart hook missing 'command': {hook}"

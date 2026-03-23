"""Tests validating that the otel-tracing hooks/hooks.json registers all
expected hook events for telemetry tracing.

These are deterministic structural tests (no LLM required, no OTel stack
required). They verify that the hooks.json in this repository is correctly
wired with all seven hook events that hook_tracer.py handles.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# The otel-tracing repo root (this file lives in tests/)
REPO_ROOT = Path(__file__).parent.parent
HOOKS_JSON = REPO_ROOT / "hooks" / "hooks.json"

# All seven hook events that should route to hook_tracer.py
EXPECTED_TRACER_EVENTS = {
    "SessionStart",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "SubagentStop",
    "PreCompact",
    "Notification",
}

HOOK_TRACER_SCRIPT = "hook_tracer.py"


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def hooks_data():
    """Load and return the parsed hooks/hooks.json from the otel-tracing repo."""
    assert HOOKS_JSON.exists(), f"hooks.json not found at {HOOKS_JSON}"
    return json.loads(HOOKS_JSON.read_text())


# ---------------------------------------------------------------------------
# Top-level structure
# ---------------------------------------------------------------------------


def test_otel_hooks_json_exists():
    assert HOOKS_JSON.exists(), f"hooks.json not found at {HOOKS_JSON}"


def test_otel_hooks_json_is_valid_json():
    data = json.loads(HOOKS_JSON.read_text())
    assert isinstance(data, dict)


def test_otel_hooks_json_has_hooks_key(hooks_data):
    assert "hooks" in hooks_data


def test_otel_hooks_top_level_value_is_dict(hooks_data):
    assert isinstance(hooks_data["hooks"], dict)


# ---------------------------------------------------------------------------
# All seven hook events must be present
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("event", sorted(EXPECTED_TRACER_EVENTS))
def test_hook_event_is_registered(hooks_data, event):
    """Each expected hook event must appear as a key in hooks.json."""
    assert event in hooks_data["hooks"], (
        f"Hook event '{event}' is missing from hooks.json. "
        f"Present events: {sorted(hooks_data['hooks'].keys())}"
    )


@pytest.mark.parametrize("event", sorted(EXPECTED_TRACER_EVENTS))
def test_hook_event_entry_is_list(hooks_data, event):
    """Each hook event section must be a list."""
    if event in hooks_data["hooks"]:
        assert isinstance(hooks_data["hooks"][event], list), (
            f"hooks['{event}'] must be a list"
        )


@pytest.mark.parametrize("event", sorted(EXPECTED_TRACER_EVENTS))
def test_hook_event_has_at_least_one_entry(hooks_data, event):
    """Each hook event section must have at least one entry."""
    if event in hooks_data["hooks"]:
        assert len(hooks_data["hooks"][event]) > 0, (
            f"hooks['{event}'] must not be empty"
        )


# ---------------------------------------------------------------------------
# hook_tracer.py must be wired into each event
# ---------------------------------------------------------------------------


def _commands_for_event(hooks_data: dict, event: str) -> list[str]:
    """Return all command strings registered under a given hook event."""
    commands = []
    for entry in hooks_data.get("hooks", {}).get(event, []):
        for hook in entry.get("hooks", []):
            cmd = hook.get("command", "")
            if cmd:
                commands.append(cmd)
    return commands


@pytest.mark.parametrize("event", sorted(EXPECTED_TRACER_EVENTS))
def test_hook_tracer_wired_into_event(hooks_data, event):
    """hook_tracer.py must be referenced in at least one command for each event."""
    if event not in hooks_data["hooks"]:
        pytest.skip(f"Event '{event}' not present in hooks.json")
    commands = _commands_for_event(hooks_data, event)
    tracer_commands = [c for c in commands if HOOK_TRACER_SCRIPT in c]
    assert tracer_commands, (
        f"No command referencing '{HOOK_TRACER_SCRIPT}' found for event '{event}'. "
        f"Commands present: {commands}"
    )


@pytest.mark.parametrize("event", sorted(EXPECTED_TRACER_EVENTS))
def test_hook_tracer_invoked_with_correct_event_flag(hooks_data, event):
    """hook_tracer.py must be invoked with --event <EventName> for each hook."""
    if event not in hooks_data["hooks"]:
        pytest.skip(f"Event '{event}' not present in hooks.json")
    commands = _commands_for_event(hooks_data, event)
    tracer_commands = [c for c in commands if HOOK_TRACER_SCRIPT in c]
    expected_flag = f"--event {event}"
    matching = [c for c in tracer_commands if expected_flag in c]
    assert matching, (
        f"No command for event '{event}' includes '{expected_flag}'. "
        f"hook_tracer commands found: {tracer_commands}"
    )


# ---------------------------------------------------------------------------
# Each hook entry must have required structure fields
# ---------------------------------------------------------------------------


def test_all_hooks_have_type_field(hooks_data):
    """Every hook entry must have a 'type' field."""
    missing = []
    for event, entries in hooks_data["hooks"].items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                if "type" not in hook:
                    missing.append(f"{event}: {hook}")
    assert not missing, f"Hooks missing 'type' field:\n" + "\n".join(missing)


def test_all_hooks_have_command_field(hooks_data):
    """Every hook entry must have a 'command' field."""
    missing = []
    for event, entries in hooks_data["hooks"].items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                if "command" not in hook:
                    missing.append(f"{event}: {hook}")
    assert not missing, f"Hooks missing 'command' field:\n" + "\n".join(missing)


def test_all_hook_commands_are_nonempty(hooks_data):
    """Every hook command string must not be empty."""
    empty = []
    for event, entries in hooks_data["hooks"].items():
        for entry in entries:
            for hook in entry.get("hooks", []):
                if "command" in hook and not hook["command"].strip():
                    empty.append(f"{event}: {hook}")
    assert not empty, f"Hooks with empty command:\n" + "\n".join(empty)


# ---------------------------------------------------------------------------
# PreToolUse must still retain the dangerous-command blocking hooks
# ---------------------------------------------------------------------------


def test_pretooluse_still_has_bash_safety_hooks(hooks_data):
    """PreToolUse must still have the Bash safety-blocking hooks (not replaced)."""
    pretooluse_entries = hooks_data["hooks"].get("PreToolUse", [])
    bash_matchers = [e for e in pretooluse_entries if e.get("matcher") == "Bash"]
    assert bash_matchers, "PreToolUse must have a 'Bash' matcher entry for safety hooks"
    bash_commands = [
        h["command"]
        for e in bash_matchers
        for h in e.get("hooks", [])
        if "command" in h
    ]
    expected_scripts = {"block-dangerous-bash.sh", "block-dangerous-git.sh", "block-dangerous-sql.sh"}
    found_scripts = {Path(c.split()[0]).name for c in bash_commands}
    assert expected_scripts.issubset(found_scripts), (
        f"Safety hook scripts missing from PreToolUse Bash matcher. "
        f"Expected: {expected_scripts}, found: {found_scripts}"
    )

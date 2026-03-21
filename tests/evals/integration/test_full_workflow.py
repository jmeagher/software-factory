"""Integration tests: full workflow state machine using memory.py with isolated CLAUDE_PLUGIN_DATA.

Run from repo root:
    python3 -m pytest tests/evals/integration/test_full_workflow.py -v

These tests are fully stubbed — no API key required.
"""
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_MEMORY_SCRIPT = Path("/home/jmeagher/.claude/plugins/cache/jsf/jsf/0.1.0/scripts/memory.py")
_WORKFLOW_SKILL = (
    Path("/home/jmeagher/.claude/plugins/cache/jsf/jsf/0.1.0/skills")
    / "jsf-workflow"
    / "SKILL.md"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def mem(args, env):
    """Run memory.py with the given args list and isolated env."""
    return subprocess.run(
        ["python3", str(_MEMORY_SCRIPT)] + args,
        capture_output=True,
        text=True,
        env=env,
    )


def write_key(key, value, env, *, tags=None, ttl=None):
    args = ["write", "--key", key, "--value", json.dumps(value)]
    if tags:
        args += ["--tags", tags]
    if ttl:
        args += ["--ttl", str(ttl)]
    result = mem(args, env)
    assert result.returncode == 0, f"write failed: {result.stderr}"
    return result.stdout.strip()


def read_key(key, env):
    result = mem(["read", "--key", key], env)
    assert result.returncode == 0, f"read failed: {result.stderr}"
    return json.loads(result.stdout)


def list_keys(env):
    result = mem(["list-keys"], env)
    assert result.returncode == 0, f"list-keys failed: {result.stderr}"
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# State machine transition tests
# ---------------------------------------------------------------------------


class TestMemoryStateMachineTransitions:
    """Walk through each workflow state transition and verify read-back."""

    def test_write_initial_request(self, mem_env):
        write_key("initial_request", {"request": "build a widget"}, mem_env)
        value = read_key("initial_request", mem_env)
        assert value == {"request": "build a widget"}

    def test_write_clarification_summary(self, mem_env):
        write_key(
            "clarification_summary",
            {"summary": "Widget with blue border", "open_questions": []},
            mem_env,
        )
        value = read_key("clarification_summary", mem_env)
        assert value["summary"] == "Widget with blue border"
        assert value["open_questions"] == []

    def test_write_implementation_plan(self, mem_env):
        plan = {
            "phases": [
                {"name": "phase-1", "description": "Core widget"},
                {"name": "phase-2", "description": "Styling"},
            ]
        }
        write_key("implementation_plan", plan, mem_env)
        value = read_key("implementation_plan", mem_env)
        assert len(value["phases"]) == 2
        assert value["phases"][0]["name"] == "phase-1"

    def test_write_phase_start(self, mem_env):
        write_key("phase_start:phase-1", {"phase": "phase-1", "status": "started"}, mem_env)
        value = read_key("phase_start:phase-1", mem_env)
        assert value["status"] == "started"

    def test_write_phase_complete(self, mem_env):
        write_key(
            "phase_complete:phase-1",
            {"phase": "phase-1", "status": "complete", "tests_pass": True},
            mem_env,
        )
        value = read_key("phase_complete:phase-1", mem_env)
        assert value["tests_pass"] is True

    def test_write_review_result(self, mem_env):
        write_key(
            "review_result:phase-1",
            {"phase": "phase-1", "approved": True, "notes": "LGTM"},
            mem_env,
        )
        value = read_key("review_result:phase-1", mem_env)
        assert value["approved"] is True

    def test_write_validation_confirmed(self, mem_env):
        write_key(
            "validation_confirmed:phase-1",
            {"phase": "phase-1", "status": "confirmed"},
            mem_env,
        )
        value = read_key("validation_confirmed:phase-1", mem_env)
        assert value["status"] == "confirmed"

    def test_write_workflow_complete(self, mem_env):
        write_key(
            "workflow_complete",
            {"summary": "All phases done", "phases_completed": ["phase-1"]},
            mem_env,
        )
        value = read_key("workflow_complete", mem_env)
        assert value["summary"] == "All phases done"


class TestMemoryGC:
    """Verify gc removes expired entries but preserves live ones."""

    def test_gc_removes_expired_entry(self, mem_env):
        write_key("expiring_key", {"data": "ephemeral"}, mem_env, ttl=1)
        # Verify it exists before expiry
        assert read_key("expiring_key", mem_env) == {"data": "ephemeral"}
        time.sleep(2)
        # Run gc
        result = mem(["gc"], mem_env)
        assert result.returncode == 0
        assert "removed 1 expired" in result.stdout
        # Should be gone now
        assert read_key("expiring_key", mem_env) is None

    def test_gc_preserves_live_entries(self, mem_env):
        write_key("live_key", {"data": "persistent"}, mem_env)
        write_key("expiring_key2", {"data": "ephemeral"}, mem_env, ttl=1)
        time.sleep(2)
        mem(["gc"], mem_env)
        # live_key must still be readable
        assert read_key("live_key", mem_env) == {"data": "persistent"}


class TestListKeys:
    """Verify list-keys returns the expected set after a full workflow population."""

    def test_list_keys_after_full_workflow(self, mem_env):
        expected_keys = [
            "initial_request",
            "clarification_summary",
            "implementation_plan",
            "phase_start:phase-1",
            "phase_complete:phase-1",
            "review_result:phase-1",
            "validation_confirmed:phase-1",
            "workflow_complete",
        ]
        for key in expected_keys:
            write_key(key, {"key": key}, mem_env)

        keys = list_keys(mem_env)
        for key in expected_keys:
            assert key in keys, f"Expected key {key!r} not found in list-keys output"

    def test_list_keys_empty_store(self, mem_env):
        keys = list_keys(mem_env)
        assert keys == {}

    def test_list_keys_count_reflects_writes(self, mem_env):
        write_key("multi_key", {"v": 1}, mem_env)
        write_key("multi_key", {"v": 2}, mem_env)
        keys = list_keys(mem_env)
        assert "multi_key" in keys
        assert keys["multi_key"]["count"] == 2


class TestMemoryIsolation:
    """Each test gets its own tmp_path via mem_env — writes in one test must not bleed into another."""

    def test_isolation_a(self, mem_env):
        write_key("isolation_test", {"owner": "test_a"}, mem_env)
        assert read_key("isolation_test", mem_env) == {"owner": "test_a"}

    def test_isolation_b(self, mem_env):
        # If isolation works, "isolation_test" should not exist here
        result = read_key("isolation_test", mem_env)
        assert result is None


# ---------------------------------------------------------------------------
# State machine ordering assertion
# ---------------------------------------------------------------------------


class TestWorkflowOrdering:
    """Verify jsf-workflow SKILL.md documents the correct phase sequence."""

    def test_workflow_skill_documents_intake_first(self):
        text = _WORKFLOW_SKILL.read_text()
        intake_pos = text.find("Intake")
        assert intake_pos != -1, "SKILL.md must mention Intake phase"

    def test_workflow_skill_documents_clarification_before_spec(self):
        text = _WORKFLOW_SKILL.read_text()
        clarification_pos = text.find("Clarification")
        spec_pos = text.find("Spec")
        assert clarification_pos != -1, "SKILL.md must mention Clarification"
        assert spec_pos != -1, "SKILL.md must mention Spec"
        assert clarification_pos < spec_pos, (
            "Clarification must appear before Spec+Plan in SKILL.md"
        )

    def test_workflow_skill_documents_implementation_after_spec(self):
        text = _WORKFLOW_SKILL.read_text()
        spec_pos = text.find("Spec")
        impl_pos = text.find("Implementation")
        assert impl_pos != -1, "SKILL.md must mention Implementation"
        assert spec_pos < impl_pos, "Spec+Plan must appear before Implementation phases"

    def test_workflow_skill_documents_done_phase_last(self):
        text = _WORKFLOW_SKILL.read_text()
        impl_pos = text.find("Implementation")
        done_pos = text.find("Done")
        assert done_pos != -1, "SKILL.md must mention Done phase"
        assert impl_pos < done_pos, "Implementation must appear before Done"

    def test_workflow_skill_references_required_memory_keys(self):
        text = _WORKFLOW_SKILL.read_text()
        required_refs = [
            "clarification_summary",
            "implementation_plan",
            "phase_start",
            "phase_complete",
            "review_result",
            "validation_confirmed",
            "workflow_complete",
        ]
        for ref in required_refs:
            assert ref in text, f"SKILL.md must reference memory key {ref!r}"


# ---------------------------------------------------------------------------
# LLM-gated end-to-end stub
# ---------------------------------------------------------------------------


@pytest.mark.llm_eval
def test_llm_full_workflow_e2e(mem_env):
    """LLM-gated: invoke start command, walk through all phases to validation_confirmed.

    Stub description:
    - Pre-populate memory with initial_request
    - Invoke the clarifier agent logic (mocked or real)
    - Assert clarification_summary written to memory
    - Invoke the planner agent logic
    - Assert implementation_plan written to memory
    - Walk each phase: write phase_start, invoke implementer, verify phase_complete
    - Invoke reviewer, verify review_result
    - Invoke validator, verify validation_confirmed
    - Verify workflow_complete written at end

    This test requires ANTHROPIC_API_KEY and --run-llm-evals flag.
    It is intentionally left as a stub to be filled in when LLM integration
    testing infrastructure is wired up.
    """
    pytest.skip("LLM e2e stub — not yet implemented beyond stub description.")

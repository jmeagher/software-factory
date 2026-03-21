"""Integration tests: resume path — pre-populate memory with partial state and verify
the resume command logic from commands/resume.md would find the right resumption point.

Run from repo root:
    python3 -m pytest tests/evals/integration/test_workflow_resume.py -v

These tests are fully stubbed — no API key required.
"""
import json
import subprocess
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_MEMORY_SCRIPT = Path("/home/jmeagher/.claude/plugins/cache/jsf/jsf/0.1.0/scripts/memory.py")
_RESUME_COMMAND = Path("/home/jmeagher/devel/software-factory/commands/resume.md")
_START_COMMAND = Path("/home/jmeagher/devel/software-factory/commands/start.md")


# ---------------------------------------------------------------------------
# Helpers (duplicated for locality — no cross-module imports between test files)
# ---------------------------------------------------------------------------


def mem(args, env):
    return subprocess.run(
        ["python3", str(_MEMORY_SCRIPT)] + args,
        capture_output=True,
        text=True,
        env=env,
    )


def write_key(key, value, env, *, tags=None):
    args = ["write", "--key", key, "--value", json.dumps(value)]
    if tags:
        args += ["--tags", tags]
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
# Helpers that simulate what the resume command logic does
# (pure Python re-implementation of the resume.md algorithm)
# ---------------------------------------------------------------------------


def _find_resumption_point(keys: dict, env) -> dict:
    """Replicate the resume.md logic:

    1. Read implementation_plan to get phase list.
    2. Walk phases in order; the first phase without validation_confirmed is the resumption point.
    3. If a phase has phase_start but no phase_complete it is 'in-progress'.
    4. If a phase has phase_complete but no review_result it needs review.
    5. If a phase has review_result but no validation_confirmed it needs validation.
    """
    if "implementation_plan" not in keys:
        return {"error": "no implementation_plan in memory"}

    plan = read_key("implementation_plan", env)
    phases = plan.get("phases", [])

    completed = []
    in_progress = None
    next_to_start = None

    for phase in phases:
        name = phase["name"]
        has_start = f"phase_start:{name}" in keys
        has_complete = f"phase_complete:{name}" in keys
        has_review = f"review_result:{name}" in keys
        has_validation = f"validation_confirmed:{name}" in keys

        if has_validation:
            completed.append(name)
        elif has_complete and has_review:
            # Waiting for validation
            in_progress = {"phase": name, "state": "awaiting_validation"}
            break
        elif has_complete:
            # Waiting for review
            in_progress = {"phase": name, "state": "awaiting_review"}
            break
        elif has_start:
            in_progress = {"phase": name, "state": "in_progress"}
            break
        else:
            next_to_start = name
            break

    return {
        "completed": completed,
        "in_progress": in_progress,
        "next_to_start": next_to_start,
    }


# ---------------------------------------------------------------------------
# Resume path tests
# ---------------------------------------------------------------------------


class TestResumePath:
    """Pre-populate memory with partial state and verify resume logic."""

    def test_resume_with_no_phases_started(self, mem_env):
        """clarification_summary and implementation_plan present, no phases started."""
        write_key("clarification_summary", {"summary": "Widget"}, mem_env)
        write_key(
            "implementation_plan",
            {
                "phases": [
                    {"name": "phase-1", "description": "Core"},
                    {"name": "phase-2", "description": "Style"},
                ]
            },
            mem_env,
        )

        keys = list_keys(mem_env)
        state = _find_resumption_point(keys, mem_env)

        assert state["completed"] == []
        assert state["in_progress"] is None
        assert state["next_to_start"] == "phase-1"

    def test_resume_with_first_phase_complete_and_validated(self, mem_env):
        """phase-1 is fully done; resume should point to phase-2."""
        write_key(
            "implementation_plan",
            {
                "phases": [
                    {"name": "phase-1", "description": "Core"},
                    {"name": "phase-2", "description": "Style"},
                ]
            },
            mem_env,
        )
        write_key("phase_start:phase-1", {"status": "started"}, mem_env)
        write_key("phase_complete:phase-1", {"status": "complete", "tests_pass": True}, mem_env)
        write_key("review_result:phase-1", {"approved": True}, mem_env)
        write_key("validation_confirmed:phase-1", {"status": "confirmed"}, mem_env)

        keys = list_keys(mem_env)
        state = _find_resumption_point(keys, mem_env)

        assert "phase-1" in state["completed"]
        assert state["in_progress"] is None
        assert state["next_to_start"] == "phase-2"

    def test_resume_with_phase_in_progress(self, mem_env):
        """phase_start written but phase_complete not yet present."""
        write_key(
            "implementation_plan",
            {
                "phases": [
                    {"name": "phase-1", "description": "Core"},
                    {"name": "phase-2", "description": "Style"},
                ]
            },
            mem_env,
        )
        write_key("phase_start:phase-1", {"status": "started"}, mem_env)

        keys = list_keys(mem_env)
        state = _find_resumption_point(keys, mem_env)

        assert state["completed"] == []
        assert state["in_progress"] is not None
        assert state["in_progress"]["phase"] == "phase-1"
        assert state["in_progress"]["state"] == "in_progress"
        assert state["next_to_start"] is None

    def test_resume_with_phase_awaiting_review(self, mem_env):
        """phase_complete present but review_result not yet written."""
        write_key(
            "implementation_plan",
            {"phases": [{"name": "phase-1", "description": "Core"}]},
            mem_env,
        )
        write_key("phase_start:phase-1", {"status": "started"}, mem_env)
        write_key("phase_complete:phase-1", {"status": "complete", "tests_pass": True}, mem_env)

        keys = list_keys(mem_env)
        state = _find_resumption_point(keys, mem_env)

        assert state["in_progress"]["phase"] == "phase-1"
        assert state["in_progress"]["state"] == "awaiting_review"

    def test_resume_with_phase_awaiting_validation(self, mem_env):
        """review_result present but validation_confirmed not yet written."""
        write_key(
            "implementation_plan",
            {"phases": [{"name": "phase-1", "description": "Core"}]},
            mem_env,
        )
        write_key("phase_start:phase-1", {"status": "started"}, mem_env)
        write_key("phase_complete:phase-1", {"status": "complete", "tests_pass": True}, mem_env)
        write_key("review_result:phase-1", {"approved": True}, mem_env)

        keys = list_keys(mem_env)
        state = _find_resumption_point(keys, mem_env)

        assert state["in_progress"]["phase"] == "phase-1"
        assert state["in_progress"]["state"] == "awaiting_validation"

    def test_resume_all_phases_complete(self, mem_env):
        """All phases validated — next_to_start should be None."""
        write_key(
            "implementation_plan",
            {"phases": [{"name": "phase-1", "description": "Core"}]},
            mem_env,
        )
        write_key("phase_start:phase-1", {"status": "started"}, mem_env)
        write_key("phase_complete:phase-1", {"status": "complete", "tests_pass": True}, mem_env)
        write_key("review_result:phase-1", {"approved": True}, mem_env)
        write_key("validation_confirmed:phase-1", {"status": "confirmed"}, mem_env)

        keys = list_keys(mem_env)
        state = _find_resumption_point(keys, mem_env)

        assert "phase-1" in state["completed"]
        assert state["in_progress"] is None
        assert state["next_to_start"] is None

    def test_resume_no_implementation_plan(self, mem_env):
        """No implementation_plan — resume logic should return an error sentinel."""
        write_key("clarification_summary", {"summary": "Widget"}, mem_env)

        keys = list_keys(mem_env)
        state = _find_resumption_point(keys, mem_env)

        assert "error" in state


# ---------------------------------------------------------------------------
# Structural content assertions on resume.md
# ---------------------------------------------------------------------------


class TestResumeCommandStructure:
    """Assert the resume command document references the right keys and logic."""

    def test_resume_md_references_list_keys(self):
        text = _RESUME_COMMAND.read_text()
        assert "list-keys" in text, "resume.md must reference list-keys operation"

    def test_resume_md_references_implementation_plan(self):
        text = _RESUME_COMMAND.read_text()
        assert "implementation_plan" in text, (
            "resume.md must reference implementation_plan memory key"
        )

    def test_resume_md_references_validation_confirmed(self):
        text = _RESUME_COMMAND.read_text()
        assert "validation_confirmed" in text, (
            "resume.md must reference validation_confirmed memory key"
        )

    def test_resume_md_asks_user_before_proceeding(self):
        text = _RESUME_COMMAND.read_text()
        # The doc should ask user before resuming
        assert "Ask" in text or "ask" in text, (
            "resume.md must instruct the agent to ask the user before proceeding"
        )

    def test_resume_md_describes_completed_phases_display(self):
        text = _RESUME_COMMAND.read_text()
        # Must tell user what phases are completed
        assert "completed" in text.lower() or "complete" in text.lower(), (
            "resume.md must mention displaying completed phases"
        )

    def test_start_md_references_initial_request_key(self):
        text = _START_COMMAND.read_text()
        assert "initial_request" in text, (
            "start.md must reference the initial_request memory key"
        )

    def test_start_md_references_gc(self):
        text = _START_COMMAND.read_text()
        assert "gc" in text, "start.md must reference memory gc operation"


# ---------------------------------------------------------------------------
# LLM-gated resume invocation stub
# ---------------------------------------------------------------------------


@pytest.mark.llm_eval
def test_llm_resume_from_partial_state(mem_env):
    """LLM-gated: pre-populate memory with partial workflow state and invoke resume.

    Stub description:
    - Write clarification_summary and implementation_plan (two phases) to memory.
    - Write phase_start:phase-1 and phase_complete:phase-1 to memory.
    - Invoke the /resume command against a real LLM Claude session.
    - Assert the LLM response:
      * Mentions phase-1 as complete (or in-progress with tests passed).
      * Identifies phase-2 as the next phase to start.
      * Asks the user "Ready to resume from phase-2?" (or equivalent).
    - Do NOT actually proceed with agent dispatch (stop at user confirmation prompt).

    This test requires ANTHROPIC_API_KEY and --run-llm-evals flag.
    It is intentionally left as a stub pending LLM integration test infrastructure.
    """
    # Pre-populate memory to the expected partial state
    write_key("initial_request", {"request": "build a widget"}, mem_env)
    write_key("clarification_summary", {"summary": "Widget with two phases"}, mem_env)
    write_key(
        "implementation_plan",
        {
            "phases": [
                {"name": "phase-1", "description": "Core widget"},
                {"name": "phase-2", "description": "Widget styling"},
            ]
        },
        mem_env,
    )
    write_key("phase_start:phase-1", {"status": "started"}, mem_env)
    write_key("phase_complete:phase-1", {"status": "complete", "tests_pass": True}, mem_env)
    write_key("review_result:phase-1", {"approved": True}, mem_env)
    write_key("validation_confirmed:phase-1", {"status": "confirmed"}, mem_env)

    # Verify pre-population is correct before invoking LLM
    keys = list_keys(mem_env)
    assert "validation_confirmed:phase-1" in keys
    assert "phase_start:phase-2" not in keys

    pytest.skip("LLM resume invocation stub — not yet implemented beyond stub description.")

"""Structural and LLM-gated tests for the /start command.

Structural tests assert the command .md file content without requiring any API keys.
LLM-gated tests are marked @pytest.mark.llm_eval and skipped unless --run-llm-evals is passed.
"""
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Structural tests
# ---------------------------------------------------------------------------


def test_start_command_file_exists(command_doc):
    """The start.md file must exist and be non-empty."""
    text = command_doc("start")
    assert text.strip(), "start.md is empty"


def test_start_references_initial_request_key(command_doc):
    """start.md must reference the 'initial_request' memory key."""
    text = command_doc("start")
    assert "initial_request" in text, "start.md must reference the 'initial_request' memory key"


def test_start_references_clarification_summary_key(command_doc):
    """start.md must reference the 'clarification_summary' memory key."""
    text = command_doc("start")
    assert "clarification_summary" in text, (
        "start.md must reference the 'clarification_summary' memory key"
    )


def test_start_references_jsf_clarifier_agent(command_doc):
    """start.md must reference the jsf-clarifier agent dispatch pattern."""
    text = command_doc("start")
    assert "jsf:clarifier" in text, (
        "start.md must reference the jsf:clarifier agent"
    )


def test_start_references_memory_script(command_doc):
    """start.md must reference memory.py for persisting initial_request."""
    text = command_doc("start")
    assert "memory.py" in text, "start.md must reference memory.py"


def test_start_references_workflow_skill(command_doc):
    """start.md must reference the jsf-workflow skill."""
    text = command_doc("start")
    assert "workflow" in text, "start.md must reference the workflow skill"


def test_start_references_gc(command_doc):
    """start.md must reference gc (garbage collection) of memory."""
    text = command_doc("start")
    assert " gc" in text or "`gc`" in text, (
        "start.md must reference memory gc to clear stale entries"
    )


def test_start_has_frontmatter_description(command_doc):
    """start.md must have a YAML frontmatter block with a description."""
    text = command_doc("start")
    assert text.startswith("---"), "start.md must start with YAML frontmatter"
    assert "description:" in text, "start.md frontmatter must include a description field"


# ---------------------------------------------------------------------------
# LLM-gated tests (stubs)
# ---------------------------------------------------------------------------


@pytest.mark.llm_eval
def test_start_writes_initial_request_to_memory():
    """LLM EVAL: Invoke /start with a synthetic request and assert that
    `initial_request` appears in memory after the command runs.
    The value should match the argument passed to /start.
    """
    pytest.skip("LLM eval stub — full implementation requires ANTHROPIC_API_KEY and Claude CLI")


@pytest.mark.llm_eval
def test_start_dispatches_clarifier_agent():
    """LLM EVAL: After /start runs, assert that a clarifier agent was dispatched
    and that `clarification_summary` eventually appears in memory as the output
    of the clarifier interaction.
    """
    pytest.skip("LLM eval stub — full implementation requires ANTHROPIC_API_KEY and Claude CLI")


@pytest.mark.llm_eval
def test_start_blocks_planning_without_clarification():
    """LLM EVAL: Assert that the start command does not advance to planning
    if `clarification_summary` is absent from memory.
    The orchestrator must gate on this key being present.
    """
    pytest.skip("LLM eval stub — full implementation requires ANTHROPIC_API_KEY and Claude CLI")

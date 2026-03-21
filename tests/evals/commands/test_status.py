"""Structural and LLM-gated tests for the /status command.

Structural tests assert the command .md file content without requiring any API keys.
LLM-gated tests are marked @pytest.mark.llm_eval and skipped unless --run-llm-evals is passed.
"""
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Structural tests
# ---------------------------------------------------------------------------


def test_status_command_file_exists(command_doc):
    """The status.md file must exist and be non-empty."""
    text = command_doc("status")
    assert text.strip(), "status.md is empty"


def test_status_references_initial_request_key(command_doc):
    """status.md must reference the 'initial_request' memory key."""
    text = command_doc("status")
    assert "initial_request" in text, (
        "status.md must reference the 'initial_request' memory key"
    )


def test_status_references_phase_complete_key(command_doc):
    """status.md must reference the 'phase_complete' memory key pattern."""
    text = command_doc("status")
    assert "phase_complete" in text, (
        "status.md must reference 'phase_complete' memory key pattern"
    )


def test_status_references_validation_confirmed_key(command_doc):
    """status.md must reference the 'validation_confirmed' memory key pattern."""
    text = command_doc("status")
    assert "validation_confirmed" in text, (
        "status.md must reference 'validation_confirmed' memory key pattern"
    )


def test_status_references_memory_list_keys(command_doc):
    """status.md must reference 'list-keys' to enumerate memory."""
    text = command_doc("status")
    assert "list-keys" in text, "status.md must reference memory.py list-keys"


def test_status_describes_clarification_state(command_doc):
    """status.md must describe showing clarification status (confirmed/pending)."""
    text = command_doc("status")
    assert "clarification" in text.lower() or "clarif" in text.lower(), (
        "status.md must describe showing clarification status"
    )


def test_status_describes_phase_display(command_doc):
    """status.md must describe displaying each phase's state."""
    text = command_doc("status")
    assert "phase" in text.lower(), "status.md must describe displaying phase state"


def test_status_describes_pending_validations(command_doc):
    """status.md must describe showing pending validations (phase_complete without validation_confirmed)."""
    text = command_doc("status")
    assert "pending" in text.lower() or "validat" in text.lower(), (
        "status.md must describe showing pending validations"
    )


def test_status_references_memory_key_count(command_doc):
    """status.md must describe showing the count of live memory entries."""
    text = command_doc("status")
    assert "count" in text.lower() or "memory keys" in text.lower() or "entries" in text.lower(), (
        "status.md must describe showing memory key count"
    )


def test_status_has_frontmatter_description(command_doc):
    """status.md must have a YAML frontmatter block with a description."""
    text = command_doc("status")
    assert text.startswith("---"), "status.md must start with YAML frontmatter"
    assert "description:" in text, "status.md frontmatter must include a description field"


# ---------------------------------------------------------------------------
# LLM-gated tests (stubs)
# ---------------------------------------------------------------------------


@pytest.mark.llm_eval
def test_status_shows_all_phase_states():
    """LLM EVAL: Pre-populate memory with a mix of completed, in-progress, and
    not-started phases. Invoke /status and assert that the output correctly
    categorizes each phase and includes commit SHAs for completed phases.
    """
    pytest.skip("LLM eval stub — full implementation requires ANTHROPIC_API_KEY and Claude CLI")


@pytest.mark.llm_eval
def test_status_highlights_pending_validation():
    """LLM EVAL: Pre-populate memory with a phase_complete entry that has no
    corresponding validation_confirmed entry. Invoke /status and assert that
    the output explicitly highlights this as a pending validation.
    """
    pytest.skip("LLM eval stub — full implementation requires ANTHROPIC_API_KEY and Claude CLI")


@pytest.mark.llm_eval
def test_status_shows_memory_summary():
    """LLM EVAL: Invoke /status and assert that the output includes a count of
    live memory entries and the file location of the memory store.
    This confirms the command reads and surfaces memory metadata.
    """
    pytest.skip("LLM eval stub — full implementation requires ANTHROPIC_API_KEY and Claude CLI")

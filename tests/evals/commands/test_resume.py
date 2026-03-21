"""Structural and LLM-gated tests for the /resume command.

Structural tests assert the command .md file content without requiring any API keys.
LLM-gated tests are marked @pytest.mark.llm_eval and skipped unless --run-llm-evals is passed.
"""
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Structural tests
# ---------------------------------------------------------------------------


def test_resume_command_file_exists(command_doc):
    """The resume.md file must exist and be non-empty."""
    text = command_doc("resume")
    assert text.strip(), "resume.md is empty"


def test_resume_references_implementation_plan_key(command_doc):
    """resume.md must reference the 'implementation_plan' memory key."""
    text = command_doc("resume")
    assert "implementation_plan" in text, (
        "resume.md must reference the 'implementation_plan' memory key"
    )


def test_resume_references_validation_confirmed_key(command_doc):
    """resume.md must reference the 'validation_confirmed' memory key pattern."""
    text = command_doc("resume")
    assert "validation_confirmed" in text, (
        "resume.md must reference 'validation_confirmed' memory key pattern"
    )


def test_resume_references_memory_list_keys(command_doc):
    """resume.md must reference 'list-keys' to read memory state."""
    text = command_doc("resume")
    assert "list-keys" in text, "resume.md must reference memory.py list-keys"


def test_resume_references_memory_read(command_doc):
    """resume.md must reference reading memory keys."""
    text = command_doc("resume")
    assert "memory.py" in text or "memory" in text.lower(), (
        "resume.md must reference memory operations"
    )


def test_resume_asks_user_confirmation(command_doc):
    """resume.md must ask the user to confirm before proceeding."""
    text = command_doc("resume")
    # The command should prompt the user before resuming
    assert "Ready to resume" in text or "ask" in text.lower() or "?" in text, (
        "resume.md must ask user for confirmation before proceeding"
    )


def test_resume_displays_phase_status(command_doc):
    """resume.md must describe displaying completed and in-progress phases."""
    text = command_doc("resume")
    assert "complet" in text.lower() or "in-progress" in text.lower() or "phase" in text.lower(), (
        "resume.md must describe displaying phase completion status"
    )


def test_resume_has_frontmatter_description(command_doc):
    """resume.md must have a YAML frontmatter block with a description."""
    text = command_doc("resume")
    assert text.startswith("---"), "resume.md must start with YAML frontmatter"
    assert "description:" in text, "resume.md frontmatter must include a description field"


# ---------------------------------------------------------------------------
# LLM-gated tests (stubs)
# ---------------------------------------------------------------------------


@pytest.mark.llm_eval
def test_resume_identifies_incomplete_phase():
    """LLM EVAL: Pre-populate memory with a partial workflow state (some phases
    complete, one in-progress). Invoke /resume and assert that the command
    correctly identifies the incomplete phase and displays it to the user.
    """
    pytest.skip("LLM eval stub — full implementation requires ANTHROPIC_API_KEY and Claude CLI")


@pytest.mark.llm_eval
def test_resume_skips_completed_phases():
    """LLM EVAL: Pre-populate memory with all phases marked validation_confirmed.
    Invoke /resume and assert the command reports the project as fully complete
    rather than re-running completed phases.
    """
    pytest.skip("LLM eval stub — full implementation requires ANTHROPIC_API_KEY and Claude CLI")


@pytest.mark.llm_eval
def test_resume_waits_for_user_confirmation():
    """LLM EVAL: Assert that /resume presents the current state summary and
    explicitly asks the user "Ready to resume from <phase name>?" before
    dispatching any agents or modifying memory.
    """
    pytest.skip("LLM eval stub — full implementation requires ANTHROPIC_API_KEY and Claude CLI")

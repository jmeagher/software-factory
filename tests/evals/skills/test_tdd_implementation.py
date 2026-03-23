"""Structural tests for jsf-tdd-implementation SKILL.md.

Tests assert required sections, red-green TDD discipline steps, phase scope
rules, unexpected failure protocol, code standards, and memory key references.

LLM eval tests (marked @pytest.mark.llm_eval) are gated on --run-llm-evals
and require ANTHROPIC_API_KEY to be set.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SKILL_NAME = "tdd-implementation"
_PLUGIN_ROOT = Path("/home/jmeagher/devel/software-factory")
_SKILL_PATH = _PLUGIN_ROOT / "skills" / SKILL_NAME / "SKILL.md"
_SCRIPTS_DIR = _PLUGIN_ROOT / "scripts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text(skill_doc) -> str:
    return skill_doc(SKILL_NAME)


# ---------------------------------------------------------------------------
# Existence
# ---------------------------------------------------------------------------

def test_skill_file_exists():
    assert _SKILL_PATH.exists(), f"SKILL.md not found at {_SKILL_PATH}"


def test_skill_file_is_non_empty():
    assert _SKILL_PATH.stat().st_size > 0, "SKILL.md is empty"


# ---------------------------------------------------------------------------
# Front-matter
# ---------------------------------------------------------------------------

def test_frontmatter_name(skill_doc):
    assert "name: tdd-implementation" in _text(skill_doc)


def test_frontmatter_version(skill_doc):
    assert "version:" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Required sections
# ---------------------------------------------------------------------------

def test_section_red_green_discipline_present(skill_doc):
    assert "## Red-Green Discipline" in _text(skill_doc)


def test_section_phase_scope_present(skill_doc):
    assert "## Phase Scope" in _text(skill_doc)


def test_section_unexpected_failure_present(skill_doc):
    assert "## On Unexpected Failure" in _text(skill_doc)


def test_section_code_standards_present(skill_doc):
    assert "## Code Standards" in _text(skill_doc)


# ---------------------------------------------------------------------------
# TDD red-green cycle steps (must all be documented)
# ---------------------------------------------------------------------------

def test_step_write_failing_test(skill_doc):
    text = _text(skill_doc)
    assert "failing test" in text.lower()


def test_step_confirm_test_fails(skill_doc):
    text = _text(skill_doc)
    assert "confirm it fails" in text.lower()


def test_step_write_minimum_code(skill_doc):
    text = _text(skill_doc)
    assert "minimum code" in text.lower()


def test_step_confirm_test_passes(skill_doc):
    text = _text(skill_doc)
    assert "confirm it passes" in text.lower()


def test_step_refactor_mentioned(skill_doc):
    text = _text(skill_doc)
    assert "refactor" in text.lower()


# ---------------------------------------------------------------------------
# Prohibition: no implementation before failing test
# ---------------------------------------------------------------------------

def test_no_implementation_before_failing_test_rule(skill_doc):
    text = _text(skill_doc)
    assert "do not write implementation code before the failing test" in text.lower()


def test_do_not_proceed_past_failing_test_rule(skill_doc):
    text = _text(skill_doc)
    assert "do not proceed past a failing test" in text.lower()


# ---------------------------------------------------------------------------
# Phase scope rules
# ---------------------------------------------------------------------------

def test_reads_implementation_plan_from_memory(skill_doc):
    assert "implementation_plan" in _text(skill_doc)


def test_scope_note_key_referenced(skill_doc):
    assert "scope_note:" in _text(skill_doc)


def test_implement_only_current_phase_rule(skill_doc):
    text = _text(skill_doc)
    assert "only what is in that phase" in text.lower()


# ---------------------------------------------------------------------------
# Unexpected failure protocol
# ---------------------------------------------------------------------------

def test_unexpected_failure_key_referenced(skill_doc):
    assert "unexpected_failure:" in _text(skill_doc)


def test_failure_stops_work_rule(skill_doc):
    text = _text(skill_doc)
    assert "stop" in text.lower()
    assert "surface the failure" in text.lower() or "do not continue" in text.lower()


def test_failure_memory_entry_has_required_fields(skill_doc):
    text = _text(skill_doc)
    assert '"test"' in text
    assert '"error"' in text
    assert '"files_changed"' in text


# ---------------------------------------------------------------------------
# Code standards
# ---------------------------------------------------------------------------

def test_no_hardcoded_credentials_rule(skill_doc):
    text = _text(skill_doc)
    assert "credentials" in text.lower() or "secrets" in text.lower()


def test_no_injection_vectors_rule(skill_doc):
    text = _text(skill_doc)
    assert "injection" in text.lower()


def test_reviewer_approval_required_before_commit(skill_doc):
    text = _text(skill_doc)
    assert "reviewer" in text.lower()
    assert "do not commit" in text.lower()


# ---------------------------------------------------------------------------
# Script path references exist on disk
# ---------------------------------------------------------------------------

def test_memory_script_exists_on_disk():
    script = _SCRIPTS_DIR / "memory.py"
    assert script.exists(), f"memory.py not found at {script}"


# ---------------------------------------------------------------------------
# LLM eval tests — skipped unless --run-llm-evals is passed
# ---------------------------------------------------------------------------

def _check_llm_prerequisites():
    """Skip the test if ANTHROPIC_API_KEY is missing or claude CLI is absent."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("requires --run-llm-evals and ANTHROPIC_API_KEY")
    if not shutil.which("claude"):
        pytest.skip("claude CLI not found on PATH")


def _call_claude(system_prompt: str, user_prompt: str, timeout: int = 60) -> str:
    """Call the claude CLI with a system prompt and user prompt, return stdout."""
    result = subprocess.run(
        ["claude", "--print", "-p", user_prompt],
        input=system_prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ},
    )
    return result.stdout


@pytest.mark.llm_eval
def test_llm_eval_tdd_refuses_implementation_before_failing_test():
    """Behavioral contract: if asked to skip the failing-test step and jump
    straight to implementation, the skill should refuse and insist the failing
    test must be written and confirmed to fail first.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "I already know what the implementation needs to do, so can I skip "
        "writing the failing test and just write the implementation code directly?"
    )
    output = _call_claude(skill_text, user_prompt)
    # Should refuse or redirect — must not say 'yes' or 'sure'
    permissive = (
        output.lower().strip().startswith("yes")
        or "you can skip" in output.lower()
        or "feel free to skip" in output.lower()
    )
    assert not permissive, (
        f"TDD skill should refuse to skip failing test but output was permissive: {output[:300]}"
    )
    # Should mention the failing test requirement
    assert "failing test" in output.lower() or "test first" in output.lower(), (
        f"Expected failing-test requirement in refusal: {output[:300]}"
    )


@pytest.mark.llm_eval
def test_llm_eval_tdd_stops_on_unexpected_test_failure():
    """Behavioral contract: when an unexpected pre-existing test failure is
    encountered mid-implementation, the skill should direct the agent to STOP
    work and surface the failure rather than continue working around it.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "I am implementing phase 'add-auth-endpoint'. While running tests I "
        "discovered that an unrelated test 'test_user_model' is now failing "
        "due to my changes. Should I continue implementing the phase or stop?"
    )
    output = _call_claude(skill_text, user_prompt)
    # Should say stop, not continue
    should_stop = (
        "stop" in output.lower()
        or "do not continue" in output.lower()
        or "halt" in output.lower()
        or "pause" in output.lower()
        or "unexpected_failure" in output.lower()
    )
    assert should_stop, (
        f"Expected stop instruction on unexpected test failure: {output[:300]}"
    )


@pytest.mark.llm_eval
def test_llm_eval_tdd_scope_limited_to_current_phase():
    """Behavioral contract: when asked to also implement features from a future
    phase while working on the current one, the skill should decline and state
    that only the current phase's scope should be implemented.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "I am working on phase 'add-login-endpoint'. I noticed that phase "
        "'add-logout-endpoint' would be quick to add at the same time. "
        "Should I implement both phases now?"
    )
    output = _call_claude(skill_text, user_prompt)
    # Should restrict to current phase only
    restrict_terms = [
        "only", "current phase", "do not", "scope", "one phase", "that phase"
    ]
    has_restriction = any(t in output.lower() for t in restrict_terms)
    assert has_restriction, (
        f"Expected phase scope restriction in output: {output[:300]}"
    )

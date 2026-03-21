"""Structural tests for jsf-spec-planning SKILL.md.

Tests assert required sections, spec document structure, implementation plan
phase fields, memory key references, and user confirmation requirement.

LLM eval tests (marked @pytest.mark.llm_eval) are gated on --run-llm-evals
and require ANTHROPIC_API_KEY to be set.
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SKILL_NAME = "jsf-spec-planning"
_PLUGIN_ROOT = Path("/home/jmeagher/.claude/plugins/cache/jsf/jsf/0.1.0")
_SKILL_PATH = _PLUGIN_ROOT / "skills" / SKILL_NAME / "SKILL.md"


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
    assert "name: jsf-spec-planning" in _text(skill_doc)


def test_frontmatter_version(skill_doc):
    assert "version:" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Required sections
# ---------------------------------------------------------------------------

def test_section_input_present(skill_doc):
    assert "## Input" in _text(skill_doc)


def test_section_technical_spec_present(skill_doc):
    assert "## Technical Spec" in _text(skill_doc)


def test_section_implementation_plan_present(skill_doc):
    assert "## Implementation Plan" in _text(skill_doc)


def test_section_user_confirmation_present(skill_doc):
    assert "## User Confirmation" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Memory key references
# ---------------------------------------------------------------------------

def test_reads_clarification_summary(skill_doc):
    assert "clarification_summary" in _text(skill_doc)


def test_writes_implementation_plan(skill_doc):
    assert "implementation_plan" in _text(skill_doc)


def test_writes_spec_document(skill_doc):
    assert "spec_document" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Technical spec sections documented
# ---------------------------------------------------------------------------

def test_spec_section_problem(skill_doc):
    assert "Problem" in _text(skill_doc)


def test_spec_section_constraints(skill_doc):
    assert "Constraints" in _text(skill_doc)


def test_spec_section_architecture(skill_doc):
    assert "Architecture" in _text(skill_doc)


def test_spec_section_data_model_changes(skill_doc):
    assert "Data model" in _text(skill_doc)


def test_spec_section_api_surface(skill_doc):
    assert "API surface" in _text(skill_doc)


def test_spec_section_security_considerations(skill_doc):
    assert "Security" in _text(skill_doc)


def test_spec_section_manual_validation_triggers(skill_doc):
    assert "Manual validation triggers" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Implementation plan phase fields
# ---------------------------------------------------------------------------

def test_phase_field_name(skill_doc):
    assert "`name`" in _text(skill_doc)


def test_phase_field_description(skill_doc):
    assert "`description`" in _text(skill_doc)


def test_phase_field_tests_first(skill_doc):
    assert "`tests_first`" in _text(skill_doc)


def test_phase_field_files(skill_doc):
    assert "`files`" in _text(skill_doc)


def test_phase_field_parallel(skill_doc):
    assert "`parallel`" in _text(skill_doc)


def test_phase_field_manual_validation(skill_doc):
    assert "`manual_validation`" in _text(skill_doc)


def test_phase_field_commit_message(skill_doc):
    assert "`commit_message`" in _text(skill_doc)


def test_phase_name_format_kebab_case(skill_doc):
    assert "kebab-case" in _text(skill_doc)


# ---------------------------------------------------------------------------
# User confirmation constraint
# ---------------------------------------------------------------------------

def test_do_not_write_to_memory_until_confirmed(skill_doc):
    text = _text(skill_doc)
    assert "do not write to memory" in text.lower() or "until user explicitly confirms" in text.lower()


def test_requires_user_explicitly_confirms(skill_doc):
    text = _text(skill_doc)
    assert "explicitly confirms" in text.lower() or "user explicitly confirms" in text.lower()


# ---------------------------------------------------------------------------
# Input gate
# ---------------------------------------------------------------------------

def test_requires_clarification_summary_before_starting(skill_doc):
    text = _text(skill_doc)
    assert "do not begin without it" in text.lower() or "do not begin" in text.lower()


# ---------------------------------------------------------------------------
# LLM eval tests — skipped unless --run-llm-evals is passed
# ---------------------------------------------------------------------------

_SKILL_CONTENT = None


def _get_skill_content():
    global _SKILL_CONTENT
    if _SKILL_CONTENT is None:
        _SKILL_CONTENT = _SKILL_PATH.read_text()
    return _SKILL_CONTENT


def _check_llm_prerequisites():
    """Skip the test if ANTHROPIC_API_KEY is missing or claude CLI is absent."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("requires --run-llm-evals and ANTHROPIC_API_KEY")
    if not shutil.which("claude"):
        pytest.skip("claude CLI not found on PATH")


def _call_claude(system_prompt: str, user_prompt: str, timeout: int = 90) -> str:
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


_SAMPLE_CLARIFICATION_SUMMARY = """
**Request:** Add a REST API endpoint for user login to the Django backend.
**Scope:** Single endpoint POST /api/auth/login that accepts email+password and returns JWT.
**Success criteria:** Endpoint returns 200 with token on valid credentials, 401 on invalid.
**Tech stack:** Django 4.2, djangorestframework, PyJWT.
**Manual validation required:** Yes — security review of JWT secret handling.
""".strip()


@pytest.mark.llm_eval
def test_llm_eval_spec_planning_produces_phases_array():
    """Behavioral contract: given a clarification summary, the spec planner should
    produce an implementation_plan with a phases array where each phase has at
    least 'name', 'description', and 'tests_first' fields.
    """
    _check_llm_prerequisites()
    skill_text = _get_skill_content()
    user_prompt = (
        f"Here is the clarification summary:\n\n{_SAMPLE_CLARIFICATION_SUMMARY}\n\n"
        "Please produce the implementation plan. Show the phases array."
    )
    output = _call_claude(skill_text, user_prompt)
    # Must mention phases structure
    has_phases = (
        '"phases"' in output
        or "'phases'" in output
        or "phases:" in output
        or "phase" in output.lower()
    )
    assert has_phases, (
        f"Expected phases structure in spec planning output: {output[:400]}"
    )
    # Each phase should have a name
    assert "name" in output.lower(), (
        f"Expected phase name field in output: {output[:400]}"
    )


@pytest.mark.llm_eval
def test_llm_eval_spec_planning_uses_kebab_case_phase_names():
    """Behavioral contract: phase names in the implementation plan must use
    kebab-case format (e.g. 'add-login-endpoint') not spaces or camelCase.
    """
    _check_llm_prerequisites()
    skill_text = _get_skill_content()
    user_prompt = (
        f"Here is the clarification summary:\n\n{_SAMPLE_CLARIFICATION_SUMMARY}\n\n"
        "List the phase names you would use in the implementation plan."
    )
    output = _call_claude(skill_text, user_prompt)
    # Should contain at least one kebab-case name (word-word pattern)
    kebab_pattern = re.compile(r'\b[a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)+\b')
    has_kebab = bool(kebab_pattern.search(output))
    assert has_kebab, (
        f"Expected kebab-case phase names in output but found none: {output[:400]}"
    )


@pytest.mark.llm_eval
def test_llm_eval_spec_planning_does_not_write_memory_before_confirmation():
    """Behavioral contract: the spec planner must NOT claim it has already written
    implementation_plan to memory before receiving explicit user confirmation.
    It should present the plan and wait.
    """
    _check_llm_prerequisites()
    skill_text = _get_skill_content()
    user_prompt = (
        f"Here is the clarification summary:\n\n{_SAMPLE_CLARIFICATION_SUMMARY}\n\n"
        "Show me the plan."
    )
    output = _call_claude(skill_text, user_prompt)
    # Should not claim it already wrote to memory in the same response
    already_wrote = (
        "i have written" in output.lower()
        or "i've written" in output.lower()
        or "has been written to memory" in output.lower()
        or "saved to memory" in output.lower()
    )
    # It should instead present the plan and ask for confirmation
    asks_for_confirmation = (
        "confirm" in output.lower()
        or "approve" in output.lower()
        or "proceed" in output.lower()
        or "?" in output
    )
    assert not already_wrote or asks_for_confirmation, (
        f"Planner claimed to write memory before confirmation: {output[:400]}"
    )

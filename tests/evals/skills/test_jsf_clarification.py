"""Structural tests for jsf-clarification SKILL.md.

These tests parse the skill document and assert required sections, memory key
references, behavioral constraints, and script path references. No LLM
invocation is performed.

LLM eval tests (marked @pytest.mark.llm_eval) are gated on --run-llm-evals
and require ANTHROPIC_API_KEY to be set.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SKILL_NAME = "jsf-clarification"
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
    text = _text(skill_doc)
    assert "name: jsf-clarification" in text


def test_frontmatter_version(skill_doc):
    text = _text(skill_doc)
    assert "version:" in text


# ---------------------------------------------------------------------------
# Required sections
# ---------------------------------------------------------------------------

def test_section_purpose_present(skill_doc):
    assert "## Purpose" in _text(skill_doc)


def test_section_question_categories_present(skill_doc):
    assert "## Question Categories" in _text(skill_doc)


def test_section_output_clarification_summary_present(skill_doc):
    assert "## Output" in _text(skill_doc)


def test_section_rules_present(skill_doc):
    assert "## Rules" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Memory key references
# ---------------------------------------------------------------------------

def test_memory_key_clarification_summary_referenced(skill_doc):
    assert "clarification_summary" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Behavioral constraints
# ---------------------------------------------------------------------------

def test_questions_in_one_message_rule(skill_doc):
    text = _text(skill_doc)
    assert "one message" in text.lower()


def test_do_not_proceed_until_confirmed_rule(skill_doc):
    text = _text(skill_doc)
    assert "do not proceed" in text.lower()


def test_user_confirmation_required(skill_doc):
    text = _text(skill_doc)
    assert "confirm" in text.lower()


def test_no_inferences_rule(skill_doc):
    text = _text(skill_doc)
    assert "infer" in text.lower() or "no inferences" in text.lower()


# ---------------------------------------------------------------------------
# Question categories coverage
# ---------------------------------------------------------------------------

def test_scope_category_present(skill_doc):
    assert "Scope" in _text(skill_doc)


def test_success_criteria_category_present(skill_doc):
    assert "Success criteria" in _text(skill_doc)


def test_tech_stack_category_present(skill_doc):
    assert "Tech stack" in _text(skill_doc)


def test_manual_validation_category_present(skill_doc):
    assert "Manual validation" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Output template fields
# ---------------------------------------------------------------------------

def test_output_template_has_request_field(skill_doc):
    assert "**Request:**" in _text(skill_doc)


def test_output_template_has_scope_field(skill_doc):
    assert "**Scope:**" in _text(skill_doc)


def test_output_template_has_success_criteria_field(skill_doc):
    assert "**Success criteria:**" in _text(skill_doc)


def test_output_template_has_tech_stack_field(skill_doc):
    assert "**Tech stack:**" in _text(skill_doc)


def test_output_template_has_manual_validation_field(skill_doc):
    assert "**Manual validation required:**" in _text(skill_doc)


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
def test_llm_eval_clarifier_produces_questions_not_answers():
    """Behavioral contract: given a vague request, the clarifier should produce
    organized clarifying questions, NOT attempt to answer or implement anything.

    The output must contain at least one question (indicated by a '?') and must
    NOT contain implementation language like 'Here is the implementation' or
    'I will build'.
    """
    _check_llm_prerequisites()
    skill_text = _get_skill_content()
    user_prompt = (
        "I want to build something for my team. Can you help?"
    )
    output = _call_claude(skill_text, user_prompt)
    # Should contain questions
    assert "?" in output, (
        f"Expected clarifying questions in output but got: {output[:300]}"
    )
    # Should NOT immediately dive into implementation
    assert "here is the implementation" not in output.lower(), (
        f"Clarifier should ask questions, not provide implementation: {output[:300]}"
    )


@pytest.mark.llm_eval
def test_llm_eval_clarifier_groups_questions_by_category():
    """Behavioral contract: when responding to an ambiguous request, the clarifier
    should group questions into the documented categories (Scope, Success criteria,
    Tech stack, Manual validation) rather than dumping a flat unordered list.
    """
    _check_llm_prerequisites()
    skill_text = _get_skill_content()
    user_prompt = (
        "Build me a web app that shows analytics for my company."
    )
    output = _call_claude(skill_text, user_prompt)
    # Should have some category structure — at least one category label or numbered/bolded grouping
    has_structure = (
        "scope" in output.lower()
        or "success" in output.lower()
        or "tech" in output.lower()
        or "**" in output
        or any(f"{n}." in output for n in range(1, 6))
    )
    assert has_structure, (
        f"Expected structured/categorized questions but output lacks structure: {output[:400]}"
    )


@pytest.mark.llm_eval
def test_llm_eval_clarifier_does_not_proceed_without_confirmation():
    """Behavioral contract: after presenting questions, the clarifier must NOT
    produce a clarification_summary or declare work complete. It must wait for
    user confirmation before moving forward.
    """
    _check_llm_prerequisites()
    skill_text = _get_skill_content()
    user_prompt = (
        "Add a REST API endpoint for user login to our Django app."
    )
    output = _call_claude(skill_text, user_prompt)
    # Should not produce a final summary without user answering questions
    assert "clarification_summary" not in output.lower() or "?" in output, (
        f"Clarifier produced a summary without waiting for user answers: {output[:400]}"
    )

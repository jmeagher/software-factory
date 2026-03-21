"""Structural tests for jsf-clarification SKILL.md.

These tests parse the skill document and assert required sections, memory key
references, behavioral constraints, and script path references. No LLM
invocation is performed.
"""
import re
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

"""Structural tests for jsf-spec-planning SKILL.md.

Tests assert required sections, spec document structure, implementation plan
phase fields, memory key references, and user confirmation requirement.
"""
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

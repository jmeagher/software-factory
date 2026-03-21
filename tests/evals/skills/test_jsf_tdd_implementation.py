"""Structural tests for jsf-tdd-implementation SKILL.md.

Tests assert required sections, red-green TDD discipline steps, phase scope
rules, unexpected failure protocol, code standards, and memory key references.
"""
from pathlib import Path

import pytest

SKILL_NAME = "jsf-tdd-implementation"
_PLUGIN_ROOT = Path("/home/jmeagher/.claude/plugins/cache/jsf/jsf/0.1.0")
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
    assert "name: jsf-tdd-implementation" in _text(skill_doc)


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

"""Structural tests for jsf-validation-gate SKILL.md.

Tests assert required sections, completion criteria, manual validation
triggers, timing rules, confirmation protocol, and memory key references.
"""
from pathlib import Path

import pytest

SKILL_NAME = "jsf-validation-gate"
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
    assert "name: jsf-validation-gate" in _text(skill_doc)


def test_frontmatter_version(skill_doc):
    assert "version:" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Required sections
# ---------------------------------------------------------------------------

def test_section_completion_criteria_present(skill_doc):
    assert "## Completion Criteria" in _text(skill_doc)


def test_section_manual_validation_triggers_present(skill_doc):
    assert "## Manual Validation Triggers" in _text(skill_doc)


def test_section_timing_present(skill_doc):
    assert "## Timing" in _text(skill_doc)


def test_section_confirmation_present(skill_doc):
    assert "## Confirmation" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Completion criteria — both conditions required
# ---------------------------------------------------------------------------

def test_automated_tests_pass_criterion(skill_doc):
    text = _text(skill_doc)
    assert "automated tests pass" in text.lower()


def test_manual_validation_confirmed_criterion(skill_doc):
    text = _text(skill_doc)
    assert "manual validation confirmed" in text.lower()


def test_both_criteria_required(skill_doc):
    text = _text(skill_doc)
    assert "both" in text.lower()


def test_not_complete_with_only_one_criterion(skill_doc):
    text = _text(skill_doc)
    assert "not complete" in text.lower() or "only one" in text.lower()


# ---------------------------------------------------------------------------
# Manual validation triggers
# ---------------------------------------------------------------------------

def test_trigger_ui_changes(skill_doc):
    text = _text(skill_doc)
    assert "ui changes" in text.lower() or "UI changes" in text


def test_trigger_api_surface_changes(skill_doc):
    text = _text(skill_doc)
    assert "api surface" in text.lower() or "API surface" in text


def test_trigger_external_integrations(skill_doc):
    text = _text(skill_doc)
    assert "external integrations" in text.lower() or "external integration" in text.lower()


def test_factory_config_manual_validation_triggers_referenced(skill_doc):
    text = _text(skill_doc)
    assert "manual_validation_triggers" in text
    assert "factory-config.json" in text


# ---------------------------------------------------------------------------
# Timing rules
# ---------------------------------------------------------------------------

def test_trigger_early_rule(skill_doc):
    text = _text(skill_doc)
    assert "as early as possible" in text.lower()


def test_parallel_phase_during_wait_rule(skill_doc):
    text = _text(skill_doc)
    assert "independent" in text.lower() or "parallelizable" in text.lower()


# ---------------------------------------------------------------------------
# Confirmation rules
# ---------------------------------------------------------------------------

def test_silence_does_not_count_rule(skill_doc):
    text = _text(skill_doc)
    assert "silence" in text.lower()


def test_ambiguous_responses_do_not_count_rule(skill_doc):
    text = _text(skill_doc)
    assert "ambiguous" in text.lower()


def test_explicit_confirmation_required(skill_doc):
    text = _text(skill_doc)
    assert "explicitly confirmed" in text.lower() or "explicitly" in text.lower()


def test_lgtm_counts_as_confirmation(skill_doc):
    assert "LGTM" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Memory key references
# ---------------------------------------------------------------------------

def test_memory_key_validation_confirmed_referenced(skill_doc):
    assert "validation_confirmed:" in _text(skill_doc)


def test_memory_write_has_confirmed_at_field(skill_doc):
    assert '"confirmed_at"' in _text(skill_doc)


def test_memory_write_has_method_field(skill_doc):
    assert '"method"' in _text(skill_doc)


# ---------------------------------------------------------------------------
# Script path references exist on disk
# ---------------------------------------------------------------------------

def test_memory_script_exists_on_disk():
    script = _SCRIPTS_DIR / "memory.py"
    assert script.exists(), f"memory.py not found at {script}"

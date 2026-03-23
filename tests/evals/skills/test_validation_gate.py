"""Structural tests for jsf-validation-gate SKILL.md.

Tests assert required sections, completion criteria, manual validation
triggers, timing rules, confirmation protocol, and memory key references.

LLM eval tests (marked @pytest.mark.llm_eval) are gated on --run-llm-evals
and require ANTHROPIC_API_KEY to be set.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SKILL_NAME = "validation-gate"
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
    assert "name: validation-gate" in _text(skill_doc)


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
def test_llm_eval_validation_gate_requires_both_criteria():
    """Behavioral contract: the validation gate must require BOTH automated tests
    passing AND explicit manual confirmation before marking a phase complete.
    Passing only one criterion must NOT be sufficient.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "All automated tests are passing for this phase. Can I mark the phase "
        "as validated and complete without waiting for the human reviewer to "
        "manually confirm?"
    )
    output = _call_claude(skill_text, user_prompt)
    # Should say no — both criteria required
    permissive = (
        output.lower().strip().startswith("yes")
        or "you can mark" in output.lower()
        or "automated tests are sufficient" in output.lower()
    )
    assert not permissive, (
        f"Validation gate should require manual confirmation too: {output[:300]}"
    )
    both_required = (
        "both" in output.lower()
        or "manual" in output.lower()
        or "confirmation" in output.lower()
        or "not complete" in output.lower()
    )
    assert both_required, (
        f"Expected 'both criteria required' language in output: {output[:300]}"
    )


@pytest.mark.llm_eval
def test_llm_eval_validation_gate_silence_does_not_count():
    """Behavioral contract: the skill must instruct the agent that silence or
    ambiguous responses from the reviewer do NOT count as explicit confirmation.
    Only a clear affirmative (e.g. 'LGTM', 'approved', 'confirmed') counts.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "I sent the validation request to the reviewer 30 minutes ago and "
        "they haven't responded. Can I treat their silence as implicit approval?"
    )
    output = _call_claude(skill_text, user_prompt)
    # Should say silence does not count
    no_silence = (
        "silence" in output.lower()
        or "does not count" in output.lower()
        or "explicit" in output.lower()
        or "no" in output.lower()
    )
    assert no_silence, (
        f"Expected silence-does-not-count guidance but got: {output[:300]}"
    )


@pytest.mark.llm_eval
def test_llm_eval_validation_gate_triggers_manual_for_api_changes():
    """Behavioral contract: when a phase includes API surface changes, the skill
    should flag that manual validation is required for that phase specifically,
    not just for UI changes.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "The phase I just implemented adds three new REST API endpoints. "
        "Do I need manual validation for this phase?"
    )
    output = _call_claude(skill_text, user_prompt)
    # Should confirm manual validation is needed for API changes
    assert "manual" in output.lower(), (
        f"Expected manual validation guidance for API changes: {output[:300]}"
    )
    yes_terms = ["yes", "required", "needed", "api surface", "should"]
    has_confirmation = any(t in output.lower() for t in yes_terms)
    assert has_confirmation, (
        f"Expected affirmation that manual validation is needed: {output[:300]}"
    )

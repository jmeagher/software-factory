"""Structural tests for jsf-workflow SKILL.md.

Tests assert required sections, lifecycle phase ordering, agent role
references, memory key references, parallelization rules, config layering,
and context discipline.

LLM eval tests (marked @pytest.mark.llm_eval) are gated on --run-llm-evals
and require ANTHROPIC_API_KEY to be set.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SKILL_NAME = "jsf-workflow"
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
    assert "name: jsf-workflow" in _text(skill_doc)


def test_frontmatter_version(skill_doc):
    assert "version:" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Required sections
# ---------------------------------------------------------------------------

def test_section_lifecycle_present(skill_doc):
    assert "## Lifecycle" in _text(skill_doc)


def test_section_config_layering_present(skill_doc):
    assert "## Config Layering" in _text(skill_doc)


def test_section_parallelization_present(skill_doc):
    assert "## Parallelization" in _text(skill_doc)


def test_section_context_discipline_present(skill_doc):
    assert "## Context Discipline" in _text(skill_doc)


def test_section_ambiguity_rule_present(skill_doc):
    assert "## Ambiguity Rule" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Phase ordering — lifecycle phases must appear in order
# ---------------------------------------------------------------------------

def test_intake_phase_present(skill_doc):
    assert "Intake" in _text(skill_doc)


def test_clarification_phase_present(skill_doc):
    assert "Clarification" in _text(skill_doc)


def test_spec_plan_phase_present(skill_doc):
    text = _text(skill_doc)
    assert "Spec" in text and "Plan" in text


def test_implementation_phases_present(skill_doc):
    assert "Implementation phases" in _text(skill_doc)


def test_done_phase_present(skill_doc):
    assert "Done" in _text(skill_doc)


def test_lifecycle_phases_are_ordered(skill_doc):
    text = _text(skill_doc)
    intake_pos = text.find("Intake")
    clarification_pos = text.find("Clarification")
    implementation_pos = text.find("Implementation phases")
    assert intake_pos < clarification_pos < implementation_pos, (
        "Lifecycle phases are not in the expected order: Intake < Clarification < Implementation"
    )


def test_do_not_skip_phases_rule(skill_doc):
    text = _text(skill_doc)
    assert "do not skip" in text.lower()


def test_do_not_reorder_phases_rule(skill_doc):
    text = _text(skill_doc)
    assert "reorder" in text.lower()


# ---------------------------------------------------------------------------
# Agent role references
# ---------------------------------------------------------------------------

def test_agent_role_jsf_clarifier_referenced(skill_doc):
    assert "jsf:jsf-clarifier" in _text(skill_doc)


def test_agent_role_jsf_planner_referenced(skill_doc):
    assert "jsf:jsf-planner" in _text(skill_doc)


def test_agent_role_jsf_implementer_referenced(skill_doc):
    assert "jsf:jsf-implementer" in _text(skill_doc)


def test_agent_role_jsf_reviewer_referenced(skill_doc):
    assert "jsf:jsf-reviewer" in _text(skill_doc)


def test_agent_role_jsf_validator_referenced(skill_doc):
    assert "jsf:jsf-validator" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Memory key references
# ---------------------------------------------------------------------------

def test_memory_key_clarification_summary_gate(skill_doc):
    assert "clarification_summary" in _text(skill_doc)


def test_memory_key_implementation_plan_gate(skill_doc):
    assert "implementation_plan" in _text(skill_doc)


def test_memory_key_phase_complete_gate(skill_doc):
    assert "phase_complete:" in _text(skill_doc)


def test_memory_key_review_result_gate(skill_doc):
    assert "review_result:" in _text(skill_doc)


def test_memory_key_validation_confirmed_gate(skill_doc):
    assert "validation_confirmed:" in _text(skill_doc)


def test_memory_key_workflow_complete(skill_doc):
    assert "workflow_complete" in _text(skill_doc)


def test_memory_key_phase_start_referenced(skill_doc):
    assert "phase_start:" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Git checkpoint references
# ---------------------------------------------------------------------------

def test_checkpoint_commit_before_phase_documented(skill_doc):
    text = _text(skill_doc)
    assert "checkpoint: before" in text


def test_feat_complete_phase_commit_documented(skill_doc):
    text = _text(skill_doc)
    assert "feat: complete phase" in text


# ---------------------------------------------------------------------------
# Config layering
# ---------------------------------------------------------------------------

def test_factory_config_json_referenced(skill_doc):
    assert "factory-config.json" in _text(skill_doc)


def test_claude_md_referenced(skill_doc):
    assert "CLAUDE.md" in _text(skill_doc)


def test_project_specific_rules_win_over_defaults(skill_doc):
    text = _text(skill_doc)
    assert "project-specific" in text.lower() or "project specific" in text.lower()


# ---------------------------------------------------------------------------
# Parallelization rules
# ---------------------------------------------------------------------------

def test_parallel_phase_requires_parallel_true(skill_doc):
    text = _text(skill_doc)
    assert "parallel: true" in text


def test_agent_context_written_before_dispatch(skill_doc):
    text = _text(skill_doc)
    assert "agent_context:" in text


# ---------------------------------------------------------------------------
# Context discipline
# ---------------------------------------------------------------------------

def test_state_passed_via_memory_not_conversation(skill_doc):
    text = _text(skill_doc)
    assert "pass state via memory" in text.lower()


def test_each_phase_runs_in_own_subagent(skill_doc):
    text = _text(skill_doc)
    assert "own subagent" in text.lower() or "its own subagent" in text.lower()


# ---------------------------------------------------------------------------
# Ambiguity rule
# ---------------------------------------------------------------------------

def test_never_assume_unstated_scope_rule(skill_doc):
    text = _text(skill_doc)
    assert "never assume" in text.lower()


def test_ask_if_unclear_rule(skill_doc):
    text = _text(skill_doc)
    assert "if unclear" in text.lower() or "if unclear: ask" in text.lower()


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
def test_llm_eval_workflow_produces_phases_in_correct_order():
    """Behavioral contract: when describing the workflow lifecycle, the skill
    must enumerate phases in the order: Intake -> Clarification -> Spec/Plan
    -> Implementation phases -> Done. It must not reorder or skip phases.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "Describe the complete lifecycle of a software factory workflow from "
        "start to finish. What are all the phases in order?"
    )
    output = _call_claude(skill_text, user_prompt)
    output_lower = output.lower()
    # All key phases must appear
    required_phases = ["intake", "clarification", "implementation"]
    for phase in required_phases:
        assert phase in output_lower, (
            f"Expected phase '{phase}' in workflow lifecycle description: {output[:400]}"
        )
    # Ordering: intake before clarification before implementation
    intake_pos = output_lower.find("intake")
    clarification_pos = output_lower.find("clarification")
    impl_pos = output_lower.find("implementation")
    if intake_pos != -1 and clarification_pos != -1 and impl_pos != -1:
        assert intake_pos < clarification_pos < impl_pos, (
            f"Workflow phases not in correct order in output: {output[:400]}"
        )


@pytest.mark.llm_eval
def test_llm_eval_workflow_refuses_to_skip_clarification():
    """Behavioral contract: when asked to skip the clarification phase and jump
    directly to implementation, the workflow skill should refuse and explain
    that phases cannot be skipped or reordered.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "The user request is very clear and I understand exactly what they want. "
        "Can I skip the clarification phase and go straight to spec/planning?"
    )
    output = _call_claude(skill_text, user_prompt)
    # Should say no — do not skip phases
    permissive = (
        output.lower().strip().startswith("yes")
        or "you can skip" in output.lower()
        or "feel free to skip" in output.lower()
    )
    assert not permissive, (
        f"Workflow skill should refuse phase skipping but was permissive: {output[:300]}"
    )
    no_skip_terms = ["do not skip", "cannot skip", "must not skip", "skip", "reorder"]
    has_restriction = any(t in output.lower() for t in no_skip_terms)
    assert has_restriction, (
        f"Expected phase-skipping restriction in output: {output[:300]}"
    )


@pytest.mark.llm_eval
def test_llm_eval_workflow_state_passed_via_memory():
    """Behavioral contract: when asked how to pass state between phases/agents,
    the workflow skill should direct the agent to use memory (not conversation
    context or inline passing) as the inter-agent communication channel.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "How should the orchestrator pass information (like the clarification "
        "summary) to the implementer subagent? Should I include it in the "
        "prompt text or use some other mechanism?"
    )
    output = _call_claude(skill_text, user_prompt)
    # Should mention memory as the mechanism
    memory_terms = ["memory", "memory.py", "memory script", "via memory"]
    has_memory_ref = any(t in output.lower() for t in memory_terms)
    assert has_memory_ref, (
        f"Expected memory-as-state-channel guidance but got: {output[:300]}"
    )

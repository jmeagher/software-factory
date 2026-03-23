"""Structural tests for jsf-memory-protocol SKILL.md.

Tests assert required sections, well-known memory keys, agent startup
protocol steps, script path references, and behavioral rules.

LLM eval tests (marked @pytest.mark.llm_eval) are gated on --run-llm-evals
and require ANTHROPIC_API_KEY to be set.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SKILL_NAME = "memory-protocol"
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
    assert "name: memory-protocol" in _text(skill_doc)


def test_frontmatter_version(skill_doc):
    assert "version:" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Required sections
# ---------------------------------------------------------------------------

def test_section_memory_file_location_present(skill_doc):
    assert "## Memory File Location" in _text(skill_doc)


def test_section_operations_present(skill_doc):
    assert "## Operations" in _text(skill_doc)


def test_section_well_known_keys_present(skill_doc):
    assert "## Well-Known Keys" in _text(skill_doc)


def test_section_agent_startup_protocol_present(skill_doc):
    assert "## Agent Startup Protocol" in _text(skill_doc)


def test_section_rules_present(skill_doc):
    assert "## Rules" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Memory operations documented
# ---------------------------------------------------------------------------

def test_write_operation_documented(skill_doc):
    assert "write" in _text(skill_doc)


def test_read_operation_documented(skill_doc):
    assert "read" in _text(skill_doc)


def test_query_operation_documented(skill_doc):
    assert "query" in _text(skill_doc)


def test_list_keys_operation_documented(skill_doc):
    assert "list-keys" in _text(skill_doc)


def test_delete_operation_documented(skill_doc):
    assert "delete" in _text(skill_doc)


def test_gc_operation_documented(skill_doc):
    assert "gc" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Well-known memory keys referenced
# ---------------------------------------------------------------------------

def test_key_clarification_summary_referenced(skill_doc):
    assert "clarification_summary" in _text(skill_doc)


def test_key_implementation_plan_referenced(skill_doc):
    assert "implementation_plan" in _text(skill_doc)


def test_key_phase_complete_referenced(skill_doc):
    assert "phase_complete:" in _text(skill_doc)


def test_key_review_result_referenced(skill_doc):
    assert "review_result:" in _text(skill_doc)


def test_key_validation_confirmed_referenced(skill_doc):
    assert "validation_confirmed:" in _text(skill_doc)


def test_key_checkpoint_referenced(skill_doc):
    assert "checkpoint:" in _text(skill_doc)


def test_key_main_trace_id_referenced(skill_doc):
    assert "main_trace_id" in _text(skill_doc)


def test_key_main_span_id_referenced(skill_doc):
    assert "main_span_id" in _text(skill_doc)


def test_key_phase_trace_referenced(skill_doc):
    assert "phase_trace:" in _text(skill_doc)


def test_key_phase_span_referenced(skill_doc):
    assert "phase_span:" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Agent startup protocol steps
# ---------------------------------------------------------------------------

def test_startup_step_list_keys(skill_doc):
    text = _text(skill_doc)
    assert "list-keys" in text


def test_startup_step_read_agent_context(skill_doc):
    text = _text(skill_doc)
    assert "agent_context" in text


def test_startup_step_export_sf_agent_id(skill_doc):
    text = _text(skill_doc)
    assert "SF_AGENT_ID" in text


def test_startup_step_export_sf_trace_id(skill_doc):
    text = _text(skill_doc)
    assert "SF_TRACE_ID" in text


# ---------------------------------------------------------------------------
# Behavioral rules
# ---------------------------------------------------------------------------

def test_gc_only_called_by_orchestrator_rule(skill_doc):
    text = _text(skill_doc)
    # Rule: gc is only called by orchestrator, not by subagents
    assert "orchestrator" in text.lower()
    assert "gc" in text


def test_sf_agent_id_required_for_writes(skill_doc):
    text = _text(skill_doc)
    assert "SF_AGENT_ID" in text
    assert "never write" in text.lower() or "must" in text.lower()


def test_ttl_option_documented(skill_doc):
    assert "--ttl" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Script path references exist on disk
# ---------------------------------------------------------------------------

def test_memory_script_exists_on_disk():
    script = _SCRIPTS_DIR / "memory.py"
    assert script.exists(), f"memory.py not found at {script}"


def test_claude_plugin_data_env_var_referenced(skill_doc):
    assert "CLAUDE_PLUGIN_DATA" in _text(skill_doc)


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
def test_llm_eval_memory_protocol_write_uses_correct_syntax():
    """Behavioral contract: when asked to store a value in memory, the agent
    should emit the correct memory.py write command syntax including --key,
    --value, and ideally --agent flags, NOT invent a different API.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "I need to write the value 'hello world' to memory under key 'test_key'. "
        "Show me the exact command to run."
    )
    output = _call_claude(skill_text, user_prompt)
    # The skill mandates using memory.py with --key and --value flags
    assert "memory.py" in output, (
        f"Expected memory.py in output but got: {output[:300]}"
    )
    assert "--key" in output, (
        f"Expected --key flag in output but got: {output[:300]}"
    )
    assert "--value" in output, (
        f"Expected --value flag in output but got: {output[:300]}"
    )


@pytest.mark.llm_eval
def test_llm_eval_memory_protocol_gc_only_for_orchestrator():
    """Behavioral contract: when a subagent asks about running gc, the skill
    should clarify that gc is reserved for the orchestrator only and should
    not be called by subagents directly.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "I am a subagent implementing a phase. Should I run the gc (garbage "
        "collection) operation on the memory store after I finish my work?"
    )
    output = _call_claude(skill_text, user_prompt)
    # The skill says gc is only called by orchestrator
    assert "orchestrator" in output.lower(), (
        f"Expected orchestrator guidance in gc response but got: {output[:300]}"
    )
    no_go_words = ["no", "not", "only", "orchestrator"]
    has_restriction = any(w in output.lower() for w in no_go_words)
    assert has_restriction, (
        f"Expected restriction language about gc but got: {output[:300]}"
    )


@pytest.mark.llm_eval
def test_llm_eval_memory_protocol_startup_sequence():
    """Behavioral contract: when an agent starts up, the skill should direct it
    to read agent_context from memory (not skip it) and export SF_AGENT_ID and
    SF_TRACE_ID environment variables.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "I just started as a new agent. What are the first memory operations "
        "I must perform before doing any work?"
    )
    output = _call_claude(skill_text, user_prompt)
    # Should mention reading agent_context and setting env vars
    assert "agent_context" in output or "list-keys" in output, (
        f"Expected agent_context or list-keys in startup guidance: {output[:300]}"
    )
    assert "SF_AGENT_ID" in output or "SF_TRACE_ID" in output, (
        f"Expected env var exports in startup guidance: {output[:300]}"
    )

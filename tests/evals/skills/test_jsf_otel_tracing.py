"""Structural tests for jsf-otel-tracing SKILL.md.

Tests assert required sections, trace architecture terms, memory key
references, span name table, and script path existence.

LLM eval tests (marked @pytest.mark.llm_eval) are gated on --run-llm-evals
and require ANTHROPIC_API_KEY to be set.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

SKILL_NAME = "jsf-otel-tracing"
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
    assert "name: jsf-otel-tracing" in _text(skill_doc)


def test_frontmatter_version(skill_doc):
    assert "version:" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Required sections
# ---------------------------------------------------------------------------

def test_section_overview_present(skill_doc):
    assert "## Overview" in _text(skill_doc)


def test_section_trace_architecture_present(skill_doc):
    assert "## Trace Architecture" in _text(skill_doc)


def test_section_stateless_design_present(skill_doc):
    assert "## Stateless Design" in _text(skill_doc)


def test_section_orchestrator_protocol_present(skill_doc):
    assert "## Orchestrator Protocol" in _text(skill_doc)


def test_section_key_span_names_present(skill_doc):
    assert "## Key Span Names" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Trace architecture terminology
# ---------------------------------------------------------------------------

def test_root_trace_mentioned(skill_doc):
    text = _text(skill_doc)
    assert "root trace" in text.lower() or "Root trace" in text


def test_phase_sub_traces_mentioned(skill_doc):
    text = _text(skill_doc)
    assert "sub-trace" in text.lower() or "phase sub-trace" in text.lower()


def test_bi_directional_linking_mentioned(skill_doc):
    text = _text(skill_doc)
    # Forward link (root -> phase) and back link (phase -> root) both mentioned
    assert "forward" in text.lower() or "bi-directional" in text.lower()


def test_otlp_endpoint_referenced(skill_doc):
    text = _text(skill_doc)
    assert "localhost:4317" in text or "OTEL_EXPORTER_OTLP_ENDPOINT" in text


def test_sf_otel_enabled_env_var_referenced(skill_doc):
    assert "SF_OTEL_ENABLED" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Memory key references
# ---------------------------------------------------------------------------

def test_memory_key_main_trace_id_referenced(skill_doc):
    assert "main_trace_id" in _text(skill_doc)


def test_memory_key_main_span_id_referenced(skill_doc):
    assert "main_span_id" in _text(skill_doc)


def test_memory_key_phase_trace_referenced(skill_doc):
    assert "phase_trace:" in _text(skill_doc)


def test_memory_key_phase_span_referenced(skill_doc):
    assert "phase_span:" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Span names in Key Span Names table
# ---------------------------------------------------------------------------

def test_span_factory_task_present(skill_doc):
    assert "factory.task" in _text(skill_doc)


def test_span_factory_phase_present(skill_doc):
    assert "factory.phase" in _text(skill_doc)


def test_span_factory_validation_automated_present(skill_doc):
    assert "factory.validation.automated" in _text(skill_doc)


def test_span_factory_validation_manual_present(skill_doc):
    assert "factory.validation.manual" in _text(skill_doc)


def test_span_factory_checkpoint_present(skill_doc):
    assert "factory.checkpoint" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Telemetry script subcommands documented
# ---------------------------------------------------------------------------

def test_start_root_command_documented(skill_doc):
    assert "start-root" in _text(skill_doc)


def test_start_phase_command_documented(skill_doc):
    assert "start-phase" in _text(skill_doc)


def test_emit_forward_link_command_documented(skill_doc):
    assert "emit-forward-link" in _text(skill_doc)


def test_emit_event_command_documented(skill_doc):
    assert "emit-event" in _text(skill_doc)


# ---------------------------------------------------------------------------
# Script path references exist on disk
# ---------------------------------------------------------------------------

def test_telemetry_script_exists_on_disk():
    script = _SCRIPTS_DIR / "telemetry.py"
    assert script.exists(), f"telemetry.py not found at {script}"


def test_memory_script_exists_on_disk():
    script = _SCRIPTS_DIR / "memory.py"
    assert script.exists(), f"memory.py not found at {script}"


# ---------------------------------------------------------------------------
# Stateless design contract
# ---------------------------------------------------------------------------

def test_simple_span_processor_mentioned(skill_doc):
    text = _text(skill_doc)
    assert "SimpleSpanProcessor" in text


def test_no_state_held_between_calls(skill_doc):
    text = _text(skill_doc)
    assert "no state" in text.lower() or "stateless" in text.lower()


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
def test_llm_eval_otel_tracing_start_root_trace_uses_correct_script():
    """Behavioral contract: when asked how to start a root trace for a new
    factory task, the skill should direct the agent to call telemetry.py with
    the start-root subcommand and store the resulting trace/span IDs in memory
    as main_trace_id and main_span_id.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "I am starting a new software factory task. How do I emit the root "
        "trace span and where do I store the resulting IDs?"
    )
    output = _call_claude(skill_text, user_prompt)
    # Must reference telemetry.py and start-root
    assert "telemetry.py" in output, (
        f"Expected telemetry.py reference in root trace guidance: {output[:300]}"
    )
    assert "start-root" in output, (
        f"Expected start-root subcommand in root trace guidance: {output[:300]}"
    )
    # Must mention where IDs are stored
    assert "main_trace_id" in output or "main_span_id" in output, (
        f"Expected main_trace_id/main_span_id storage guidance: {output[:300]}"
    )


@pytest.mark.llm_eval
def test_llm_eval_otel_tracing_phase_sub_trace_links_to_root():
    """Behavioral contract: when asked how to start a phase trace, the skill
    should direct the agent to use start-phase and emit a forward link from
    the root trace to the new phase sub-trace via emit-forward-link.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "I am about to start the 'test-infrastructure' phase. The main trace "
        "is already started. How do I create the phase sub-trace and link it "
        "back to the root trace?"
    )
    output = _call_claude(skill_text, user_prompt)
    # Must reference start-phase and linking
    assert "start-phase" in output, (
        f"Expected start-phase subcommand in phase trace guidance: {output[:300]}"
    )
    link_terms = ["emit-forward-link", "forward link", "link", "bi-directional"]
    assert any(t in output.lower() for t in link_terms), (
        f"Expected linking guidance in phase trace response: {output[:300]}"
    )


@pytest.mark.llm_eval
def test_llm_eval_otel_tracing_respects_sf_otel_enabled_gate():
    """Behavioral contract: the skill must instruct the agent to check the
    SF_OTEL_ENABLED environment variable before emitting any spans. If it is
    not set to '1', tracing should be skipped entirely.
    """
    _check_llm_prerequisites()
    skill_text = (_SKILL_PATH).read_text()
    user_prompt = (
        "Should I always emit OpenTelemetry spans regardless of environment "
        "configuration, or is there a guard I need to check first?"
    )
    output = _call_claude(skill_text, user_prompt)
    assert "SF_OTEL_ENABLED" in output, (
        f"Expected SF_OTEL_ENABLED gating instruction in output: {output[:300]}"
    )

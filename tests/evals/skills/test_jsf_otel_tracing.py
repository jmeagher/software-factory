"""Structural tests for jsf-otel-tracing SKILL.md.

Tests assert required sections, trace architecture terms, memory key
references, span name table, and script path existence.
"""
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

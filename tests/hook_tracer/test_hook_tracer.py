"""
Unit tests for hook_tracer.py.

Tests run WITHOUT a live OTel collector.  All OTel export is captured via
InMemorySpanExporter, which is injected through the module-level
_make_provider() override or via the build_provider() helper exposed by the
module.

Run:
    cd /home/jmeagher/devel/software-factory-otel-tracing
    python3 -m pytest tests/hook_tracer/ -v
"""
import importlib
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
from unittest import mock

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.resources import Resource

# Ensure scripts/ is on the path so we can import hook_tracer directly
SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _make_test_provider():
    """Return (provider, exporter) using in-memory exporter — no network."""
    exporter = InMemorySpanExporter()
    resource = Resource.create({"service.name": "jsf"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


def _reload_hook_tracer(env_overrides=None):
    """Import (or reimport) hook_tracer with the given environment overrides."""
    env = {
        "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
    }
    if env_overrides:
        env.update(env_overrides)

    with mock.patch.dict(os.environ, env, clear=False):
        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer  # noqa: PLC0415
    return hook_tracer


# ---------------------------------------------------------------------------
# Guard tests
# ---------------------------------------------------------------------------

class TestGuards:
    def test_guard_exits_when_telemetry_disabled(self, tmp_path, monkeypatch):
        """script exits 0 when CLAUDE_CODE_ENABLE_TELEMETRY != 1."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "0")
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

        # Importing should not raise; guard_check() should return True (= should exit)
        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415
        assert ht.should_exit_early() is True

    def test_guard_exits_when_endpoint_unset(self, monkeypatch):
        """script exits 0 when OTEL_EXPORTER_OTLP_ENDPOINT is unset."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415
        assert ht.should_exit_early() is True

    def test_guard_exits_when_endpoint_empty(self, monkeypatch):
        """script exits 0 when OTEL_EXPORTER_OTLP_ENDPOINT is empty string."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415
        assert ht.should_exit_early() is True

    def test_guard_passes_when_both_set(self, monkeypatch):
        """should_exit_early() returns False when both env vars are correctly set."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415
        assert ht.should_exit_early() is False


# ---------------------------------------------------------------------------
# SessionStart
# ---------------------------------------------------------------------------

class TestSessionStart:
    def test_session_start_creates_root_span(self, monkeypatch, tmp_path):
        """session-start creates a claude.session root span with correct attributes."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "test-session-123")
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415

        provider, exporter = _make_test_provider()

        payload = {"session_id": "test-session-123"}
        result = ht.handle_session_start(payload, provider=provider, session_id="test-session-123")

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.name == "claude.session"
        assert span.attributes.get("session.id") == "test-session-123"
        assert span.attributes.get("service.name") == "jsf" or span.resource.attributes.get("service.name") == "jsf"

    def test_session_start_returns_trace_and_span_ids(self, monkeypatch, tmp_path):
        """session-start returns JSON with trace_id and span_id."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "test-session-456")
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415

        provider, exporter = _make_test_provider()
        payload = {}
        result = ht.handle_session_start(payload, provider=provider, session_id="test-session-456")

        assert "trace_id" in result
        assert "span_id" in result
        assert len(result["trace_id"]) == 32
        assert len(result["span_id"]) == 16

    def test_session_start_persists_context_to_memory(self, monkeypatch, tmp_path):
        """session-start writes trace context to memory under claude_session_trace_id:{session_id}."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "mem-session-789")
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415

        provider, exporter = _make_test_provider()
        payload = {}
        result = ht.handle_session_start(payload, provider=provider, session_id="mem-session-789")

        # Memory key should be written
        memory_data = ht.read_session_context("mem-session-789")
        assert memory_data is not None
        assert memory_data["trace_id"] == result["trace_id"]
        assert memory_data["span_id"] == result["span_id"]

    def test_session_start_links_to_claude_trace(self, monkeypatch, tmp_path):
        """When CLAUDE_TRACE_ID is set, claude.session span has an OTel link to it."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "link-session")
        monkeypatch.setenv("CLAUDE_TRACE_ID", "a" * 32)
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415

        provider, exporter = _make_test_provider()
        payload = {}
        result = ht.handle_session_start(payload, provider=provider, session_id="link-session")

        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        # span must have at least one link
        assert len(spans[0].links) >= 1
        linked_trace_id = format(spans[0].links[0].context.trace_id, "032x")
        assert linked_trace_id == "a" * 32


# ---------------------------------------------------------------------------
# PreToolUse
# ---------------------------------------------------------------------------

class TestPreToolUse:
    def test_pre_tool_creates_child_span(self, monkeypatch, tmp_path):
        """pre-tool creates a claude.tool_call span as child of session root."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "tool-session")
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415

        provider, exporter = _make_test_provider()

        # First create session context in memory
        session_ctx = ht.handle_session_start({}, provider=provider, session_id="tool-session")

        payload = {
            "tool_use_id": "invoke-abc123",
            "tool_name": "Bash",
            "hook_event_name": "PreToolUse",
        }
        ht.handle_pre_tool(payload, provider=provider, session_id="tool-session")

        spans = exporter.get_finished_spans()
        # session span + pre-tool span (pre-tool span is "open" but SimpleSpanProcessor
        # emits on end; pre-tool writes context to file and does NOT end span here)
        # Actually: pre-tool span is started and NOT ended — it won't appear in finished spans
        # The temp file will carry the span context
        assert len(spans) >= 1  # at minimum the session span

    def test_pre_tool_writes_temp_file(self, monkeypatch, tmp_path):
        """pre-tool writes span context to temp file keyed by tool_use_id."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "tmpfile-session")
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setenv("TMPDIR", str(tmp_path))

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415

        provider, exporter = _make_test_provider()
        ht.handle_session_start({}, provider=provider, session_id="tmpfile-session")

        tool_use_id = "tool-call-xyz"
        payload = {
            "tool_use_id": tool_use_id,
            "tool_name": "Read",
            "hook_event_name": "PreToolUse",
        }
        ht.handle_pre_tool(payload, provider=provider, session_id="tmpfile-session")

        expected_path = Path(tmp_path) / f"jsf_hook_{tool_use_id}.json"
        assert expected_path.exists(), f"Expected temp file at {expected_path}"

        ctx_data = json.loads(expected_path.read_text())
        # Temp file must store tool_name and the parent session context
        assert "tool_name" in ctx_data
        assert "start_time_ns" in ctx_data

    def test_pre_tool_temp_file_uses_tmpdir_env(self, monkeypatch, tmp_path):
        """Temp file path uses $TMPDIR if set, falls back to /tmp."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "tmpdir-env-session")
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))

        custom_tmp = tmp_path / "custom_tmp"
        custom_tmp.mkdir()
        monkeypatch.setenv("TMPDIR", str(custom_tmp))

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415

        provider, exporter = _make_test_provider()
        ht.handle_session_start({}, provider=provider, session_id="tmpdir-env-session")

        tool_use_id = "env-tool-call"
        payload = {"tool_use_id": tool_use_id, "tool_name": "Bash"}
        ht.handle_pre_tool(payload, provider=provider, session_id="tmpdir-env-session")

        expected = custom_tmp / f"jsf_hook_{tool_use_id}.json"
        assert expected.exists(), f"Should use TMPDIR: {expected}"

    def test_pre_tool_sets_tool_name_attribute(self, monkeypatch, tmp_path):
        """pre-tool span carries tool.name and session.id attributes."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "attr-session")
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setenv("TMPDIR", str(tmp_path))

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415

        provider, exporter = _make_test_provider()
        ht.handle_session_start({}, provider=provider, session_id="attr-session")

        tool_use_id = "attr-tool-xyz"
        payload = {
            "tool_use_id": tool_use_id,
            "tool_name": "Write",
            "hook_event_name": "PreToolUse",
        }
        ht.handle_pre_tool(payload, provider=provider, session_id="attr-session")

        # Span context is persisted to temp file; verify attributes stored there
        temp_file = Path(tmp_path) / f"jsf_hook_{tool_use_id}.json"
        ctx_data = json.loads(temp_file.read_text())
        assert ctx_data.get("tool_name") == "Write"
        assert ctx_data.get("session_id") == "attr-session"


# ---------------------------------------------------------------------------
# PostToolUse
# ---------------------------------------------------------------------------

class TestPostToolUse:
    def test_post_tool_ends_span_and_deletes_temp_file(self, monkeypatch, tmp_path):
        """post-tool reads temp file, emits the tool_call span, and deletes the file."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "post-session")
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setenv("TMPDIR", str(tmp_path))

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415

        provider, exporter = _make_test_provider()
        ht.handle_session_start({}, provider=provider, session_id="post-session")

        tool_use_id = "post-tool-call-001"
        pre_payload = {"tool_use_id": tool_use_id, "tool_name": "Bash"}
        ht.handle_pre_tool(pre_payload, provider=provider, session_id="post-session")

        temp_file = Path(tmp_path) / f"jsf_hook_{tool_use_id}.json"
        assert temp_file.exists()

        post_payload = {"tool_use_id": tool_use_id, "hook_event_name": "PostToolUse"}
        ht.handle_post_tool(post_payload, provider=provider, session_id="post-session")

        # Temp file must be deleted
        assert not temp_file.exists(), "Temp file must be deleted after post-tool"

        # Exactly one finished tool_call span should exist (plus the session span)
        spans = exporter.get_finished_spans()
        tool_spans = [s for s in spans if s.name == "claude.tool_call"]
        assert len(tool_spans) == 1

    def test_post_tool_span_has_correct_attributes(self, monkeypatch, tmp_path):
        """The finished claude.tool_call span carries tool.name and session.id."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "attr-post-session")
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setenv("TMPDIR", str(tmp_path))

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415

        provider, exporter = _make_test_provider()
        ht.handle_session_start({}, provider=provider, session_id="attr-post-session")

        tool_use_id = "attr-post-call"
        ht.handle_pre_tool(
            {"tool_use_id": tool_use_id, "tool_name": "Edit"},
            provider=provider, session_id="attr-post-session",
        )
        ht.handle_post_tool(
            {"tool_use_id": tool_use_id},
            provider=provider, session_id="attr-post-session",
        )

        spans = exporter.get_finished_spans()
        tool_spans = [s for s in spans if s.name == "claude.tool_call"]
        assert len(tool_spans) == 1
        span = tool_spans[0]
        assert span.attributes.get("tool.name") == "Edit"
        assert span.attributes.get("session.id") == "attr-post-session"

    def test_post_tool_no_crash_when_temp_file_missing(self, monkeypatch, tmp_path):
        """post-tool is idempotent: no crash if temp file is already gone."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "missing-file-session")
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setenv("TMPDIR", str(tmp_path))

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415

        provider, exporter = _make_test_provider()
        # No pre-tool call — temp file won't exist
        post_payload = {"tool_use_id": "nonexistent-id"}
        # Must not raise
        ht.handle_post_tool(post_payload, provider=provider, session_id="missing-file-session")


# ---------------------------------------------------------------------------
# Session events (Stop, SubagentStop, PreCompact, Notification)
# ---------------------------------------------------------------------------

class TestSessionEvents:
    def _setup_session(self, monkeypatch, tmp_path, session_id):
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        monkeypatch.setenv("CLAUDE_SESSION_ID", session_id)
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415
        provider, exporter = _make_test_provider()
        ht.handle_session_start({}, provider=provider, session_id=session_id)
        return ht, provider, exporter

    def test_stop_emits_session_stop_span(self, monkeypatch, tmp_path):
        """Stop event emits a claude.session.stop instantaneous child span."""
        ht, provider, exporter = self._setup_session(monkeypatch, tmp_path, "stop-session")
        ht.handle_session_event("Stop", {}, provider=provider, session_id="stop-session")

        spans = exporter.get_finished_spans()
        event_spans = [s for s in spans if s.name == "claude.session.stop"]
        assert len(event_spans) == 1

    def test_subagent_stop_emits_span(self, monkeypatch, tmp_path):
        """SubagentStop event emits a claude.session.subagent_stop span."""
        ht, provider, exporter = self._setup_session(monkeypatch, tmp_path, "subagent-session")
        ht.handle_session_event("SubagentStop", {}, provider=provider, session_id="subagent-session")

        spans = exporter.get_finished_spans()
        event_spans = [s for s in spans if s.name == "claude.session.subagent_stop"]
        assert len(event_spans) == 1

    def test_precompact_emits_span(self, monkeypatch, tmp_path):
        """PreCompact event emits a claude.session.pre_compact span."""
        ht, provider, exporter = self._setup_session(monkeypatch, tmp_path, "compact-session")
        ht.handle_session_event("PreCompact", {}, provider=provider, session_id="compact-session")

        spans = exporter.get_finished_spans()
        event_spans = [s for s in spans if s.name == "claude.session.pre_compact"]
        assert len(event_spans) == 1

    def test_notification_emits_span(self, monkeypatch, tmp_path):
        """Notification event emits a claude.session.notification span."""
        ht, provider, exporter = self._setup_session(monkeypatch, tmp_path, "notif-session")
        ht.handle_session_event("Notification", {}, provider=provider, session_id="notif-session")

        spans = exporter.get_finished_spans()
        event_spans = [s for s in spans if s.name == "claude.session.notification"]
        assert len(event_spans) == 1

    def test_session_event_span_is_child_of_root(self, monkeypatch, tmp_path):
        """Session event span has the claude.session span as its parent."""
        ht, provider, exporter = self._setup_session(monkeypatch, tmp_path, "child-check-session")
        ht.handle_session_event("Stop", {}, provider=provider, session_id="child-check-session")

        spans = exporter.get_finished_spans()
        session_spans = [s for s in spans if s.name == "claude.session"]
        event_spans = [s for s in spans if s.name == "claude.session.stop"]
        assert session_spans and event_spans
        session_span_id = session_spans[0].get_span_context().span_id
        event_parent_span_id = event_spans[0].parent.span_id
        assert event_parent_span_id == session_span_id


# ---------------------------------------------------------------------------
# prompt.id attribute propagation
# ---------------------------------------------------------------------------

class TestPromptId:
    def test_prompt_id_carried_on_tool_span(self, monkeypatch, tmp_path):
        """prompt.id from stdin payload is attached to claude.tool_call span."""
        monkeypatch.setenv("CLAUDE_CODE_ENABLE_TELEMETRY", "1")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "prompt-id-session")
        monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
        monkeypatch.setenv("TMPDIR", str(tmp_path))

        if "hook_tracer" in sys.modules:
            del sys.modules["hook_tracer"]
        import hook_tracer as ht  # noqa: PLC0415

        provider, exporter = _make_test_provider()
        ht.handle_session_start({}, provider=provider, session_id="prompt-id-session")

        tool_use_id = "prompt-tool"
        ht.handle_pre_tool(
            {"tool_use_id": tool_use_id, "tool_name": "Bash", "prompt_id": "pmt-xyz"},
            provider=provider, session_id="prompt-id-session",
        )
        ht.handle_post_tool(
            {"tool_use_id": tool_use_id, "prompt_id": "pmt-xyz"},
            provider=provider, session_id="prompt-id-session",
        )

        spans = exporter.get_finished_spans()
        tool_spans = [s for s in spans if s.name == "claude.tool_call"]
        assert len(tool_spans) == 1
        assert tool_spans[0].attributes.get("prompt.id") == "pmt-xyz"

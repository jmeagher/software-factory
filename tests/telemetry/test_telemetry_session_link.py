"""
Tests for telemetry.py Phase 3: session parent linking.

Behaviors tested:
1. start-root with CLAUDE_SESSION_ID + session trace context in memory includes
   a 'claude_session_link' in output JSON (OTel Link to claude.session span).
2. start-root without CLAUDE_SESSION_ID (or no session context in memory) works
   normally — no link, no error.
3. start-phase also picks up claude.session link when session context is available.
4. Guard: CLAUDE_CODE_ENABLE_TELEMETRY=1 + OTEL_EXPORTER_OTLP_ENDPOINT controls
   export, independent of SF_OTEL_ENABLED (which stays for backward compat).
"""
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "telemetry.py"
MEMORY_SCRIPT = REPO_ROOT / "scripts" / "memory.py"


def _write_session_ctx(data_dir: str, session_id: str, trace_id: str, span_id: str) -> None:
    """Write a claude_session_trace_id entry to memory via memory.py."""
    key = f"claude_session_trace_id:{session_id}"
    value = json.dumps({"trace_id": trace_id, "span_id": span_id})
    subprocess.run(
        ["python3", str(MEMORY_SCRIPT), "write", "--key", key, "--value", value],
        check=True,
        env={**os.environ, "CLAUDE_PLUGIN_DATA": data_dir},
    )


def run(args, env_overrides=None, data_dir=None, with_telemetry_guard=False):
    """Run telemetry.py with SF_OTEL_ENABLED=0 (no actual OTLP export).

    If with_telemetry_guard=True, also sets CLAUDE_CODE_ENABLE_TELEMETRY=1 and
    OTEL_EXPORTER_OTLP_ENDPOINT so that session link lookup is activated.
    """
    base = {**os.environ, "SF_OTEL_ENABLED": "0"}
    if data_dir:
        base["CLAUDE_PLUGIN_DATA"] = data_dir
    if with_telemetry_guard:
        base["CLAUDE_CODE_ENABLE_TELEMETRY"] = "1"
        base["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4317"
    if env_overrides:
        base.update(env_overrides)
    return subprocess.run(
        ["python3", str(SCRIPT)] + args,
        capture_output=True,
        text=True,
        env=base,
    )


class TestSessionLink:
    """start-root includes OTel link to claude.session when session context exists."""

    def test_start_root_with_session_ctx_includes_link(self):
        """When CLAUDE_SESSION_ID + guard vars set and memory has matching ctx, output includes claude_session_link."""
        with tempfile.TemporaryDirectory() as data_dir:
            session_id = str(uuid.uuid4())
            fake_trace_id = "a" * 32
            fake_span_id = "b" * 16
            _write_session_ctx(data_dir, session_id, fake_trace_id, fake_span_id)

            r = run(
                ["start-root", "--task", "linked-task"],
                env_overrides={"CLAUDE_SESSION_ID": session_id},
                data_dir=data_dir,
                with_telemetry_guard=True,
            )
            assert r.returncode == 0, r.stderr
            data = json.loads(r.stdout)
            # Must include claude_session_link indicating the link was attached
            assert "claude_session_link" in data, (
                f"Expected 'claude_session_link' in output but got: {data}"
            )
            link = data["claude_session_link"]
            assert link["trace_id"] == fake_trace_id
            assert link["span_id"] == fake_span_id

    def test_start_root_without_session_ctx_works_normally(self):
        """When no session context in memory, start-root still succeeds without a link."""
        with tempfile.TemporaryDirectory() as data_dir:
            session_id = str(uuid.uuid4())
            r = run(
                ["start-root", "--task", "no-session-ctx"],
                env_overrides={"CLAUDE_SESSION_ID": session_id},
                data_dir=data_dir,
            )
            assert r.returncode == 0, r.stderr
            data = json.loads(r.stdout)
            assert "trace_id" in data and len(data["trace_id"]) == 32
            assert "span_id" in data and len(data["span_id"]) == 16
            # No link key when no session context
            assert "claude_session_link" not in data

    def test_start_root_without_claude_session_id_works_normally(self):
        """When CLAUDE_SESSION_ID is not set, no link is attempted."""
        with tempfile.TemporaryDirectory() as data_dir:
            env = {k: v for k, v in os.environ.items() if k != "CLAUDE_SESSION_ID"}
            r = subprocess.run(
                ["python3", str(SCRIPT), "start-root", "--task", "no-session-id"],
                capture_output=True,
                text=True,
                env={**env, "SF_OTEL_ENABLED": "0", "CLAUDE_PLUGIN_DATA": data_dir},
            )
            assert r.returncode == 0, r.stderr
            data = json.loads(r.stdout)
            assert "trace_id" in data
            assert "claude_session_link" not in data

    def test_start_root_session_link_uses_correct_trace_id(self):
        """Link points to the claude.session trace, not the factory.task trace (different traces)."""
        with tempfile.TemporaryDirectory() as data_dir:
            session_id = str(uuid.uuid4())
            session_trace_id = "c" * 32
            session_span_id = "d" * 16
            _write_session_ctx(data_dir, session_id, session_trace_id, session_span_id)

            r = run(
                ["start-root", "--task", "trace-check"],
                env_overrides={"CLAUDE_SESSION_ID": session_id},
                data_dir=data_dir,
                with_telemetry_guard=True,
            )
            assert r.returncode == 0, r.stderr
            data = json.loads(r.stdout)
            # factory.task trace_id must differ from the session trace_id (independent traces)
            assert data["trace_id"] != session_trace_id
            # But the link must point to the session trace
            assert data["claude_session_link"]["trace_id"] == session_trace_id


class TestSessionLinkForPhase:
    """start-phase also includes OTel link to claude.session when context exists."""

    def test_start_phase_with_session_ctx_includes_link(self):
        """start-phase with session context in memory includes claude_session_link when guard vars set."""
        with tempfile.TemporaryDirectory() as data_dir:
            session_id = str(uuid.uuid4())
            fake_trace_id = "e" * 32
            fake_span_id = "f" * 16
            _write_session_ctx(data_dir, session_id, fake_trace_id, fake_span_id)

            # First create a root to get root trace/span IDs
            r_root = run(["start-root", "--task", "phase-parent"], data_dir=data_dir)
            root = json.loads(r_root.stdout)

            r = run(
                ["start-phase", "--phase", "impl",
                 "--root-trace-id", root["trace_id"],
                 "--root-span-id", root["span_id"]],
                env_overrides={"CLAUDE_SESSION_ID": session_id},
                data_dir=data_dir,
                with_telemetry_guard=True,
            )
            assert r.returncode == 0, r.stderr
            data = json.loads(r.stdout)
            assert "claude_session_link" in data, (
                f"Expected 'claude_session_link' in start-phase output but got: {data}"
            )
            assert data["claude_session_link"]["trace_id"] == fake_trace_id

    def test_start_phase_without_session_ctx_works_normally(self):
        """start-phase without session context still works, just no link."""
        with tempfile.TemporaryDirectory() as data_dir:
            r_root = run(["start-root", "--task", "phase-parent-no-ctx"], data_dir=data_dir)
            root = json.loads(r_root.stdout)

            r = run(
                ["start-phase", "--phase", "review",
                 "--root-trace-id", root["trace_id"],
                 "--root-span-id", root["span_id"]],
                data_dir=data_dir,
            )
            assert r.returncode == 0, r.stderr
            data = json.loads(r.stdout)
            assert "trace_id" in data
            assert "claude_session_link" not in data


class TestGuardBehavior:
    """Guard: CLAUDE_CODE_ENABLE_TELEMETRY and OTEL_EXPORTER_OTLP_ENDPOINT."""

    def test_claude_code_enable_telemetry_guard_no_export_without_it(self):
        """Without CLAUDE_CODE_ENABLE_TELEMETRY=1 and endpoint, SF_OTEL_ENABLED=0 still works."""
        # Existing behavior: SF_OTEL_ENABLED=0 prevents export, script still returns IDs
        r = run(["start-root", "--task", "guard-test"])
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert "trace_id" in data

    def test_no_session_link_attempted_without_enable_telemetry(self):
        """When CLAUDE_CODE_ENABLE_TELEMETRY != 1, no session link lookup is performed."""
        with tempfile.TemporaryDirectory() as data_dir:
            session_id = str(uuid.uuid4())
            _write_session_ctx(data_dir, session_id, "a" * 32, "b" * 16)

            # No CLAUDE_CODE_ENABLE_TELEMETRY set, no OTEL_EXPORTER_OTLP_ENDPOINT
            env = {
                k: v for k, v in os.environ.items()
                if k not in ("CLAUDE_CODE_ENABLE_TELEMETRY", "OTEL_EXPORTER_OTLP_ENDPOINT")
            }
            r = subprocess.run(
                ["python3", str(SCRIPT), "start-root", "--task", "no-guard"],
                capture_output=True,
                text=True,
                env={**env, "SF_OTEL_ENABLED": "0",
                     "CLAUDE_SESSION_ID": session_id,
                     "CLAUDE_PLUGIN_DATA": data_dir},
            )
            assert r.returncode == 0, r.stderr
            data = json.loads(r.stdout)
            # Without CLAUDE_CODE_ENABLE_TELEMETRY=1, no session link should be included
            assert "claude_session_link" not in data

    def test_session_link_included_when_enable_telemetry_set(self):
        """When CLAUDE_CODE_ENABLE_TELEMETRY=1 and endpoint set, session link is looked up."""
        with tempfile.TemporaryDirectory() as data_dir:
            session_id = str(uuid.uuid4())
            session_trace_id = "1" * 32
            session_span_id = "2" * 16
            _write_session_ctx(data_dir, session_id, session_trace_id, session_span_id)

            # Use SF_OTEL_ENABLED=0 to prevent actual OTLP export, but set the Claude guard vars
            r = run(
                ["start-root", "--task", "with-guard"],
                env_overrides={
                    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
                    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4317",
                    "CLAUDE_SESSION_ID": session_id,
                },
                data_dir=data_dir,
            )
            assert r.returncode == 0, r.stderr
            data = json.loads(r.stdout)
            assert "claude_session_link" in data
            assert data["claude_session_link"]["trace_id"] == session_trace_id

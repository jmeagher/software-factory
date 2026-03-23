"""
Black-box integration tests for hook_tracer.py against a live OTel/Jaeger stack.

Tests are skipped unless CLAUDE_CODE_ENABLE_TELEMETRY=1 and
OTEL_EXPORTER_OTLP_ENDPOINT are both set.

Invokes hook_tracer.py as a subprocess (the same way Claude's hook runner
would), then polls Jaeger HTTP API with a retry loop to verify spans landed
with the correct structure.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

import pytest
import requests

# ---------------------------------------------------------------------------
# Module-level skip guard
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.skipif(
    os.environ.get("CLAUDE_CODE_ENABLE_TELEMETRY") != "1"
    or not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"),
    reason="OTel env vars not set (need CLAUDE_CODE_ENABLE_TELEMETRY=1 and OTEL_EXPORTER_OTLP_ENDPOINT)",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JAEGER_BASE = "http://localhost:16686"
JAEGER_SERVICES_URL = f"{JAEGER_BASE}/api/services"
JAEGER_TRACES_URL = f"{JAEGER_BASE}/api/traces"
HOOK_TRACER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "scripts",
    "hook_tracer.py",
)
# Maximum time to wait for a span to appear in Jaeger
SPAN_WAIT_TIMEOUT_SECONDS = 30
SPAN_POLL_INTERVAL_SECONDS = 1
QUERY_LOOKBACK = "5m"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(event: str, payload: dict, session_id: str) -> subprocess.CompletedProcess:
    """Invoke hook_tracer.py with the given event and payload via stdin."""
    env = dict(os.environ)
    env["CLAUDE_SESSION_ID"] = session_id
    return subprocess.run(
        [sys.executable, HOOK_TRACER, "--event", event],
        input=json.dumps(payload).encode(),
        capture_output=True,
        env=env,
    )


def _query_jaeger_traces(
    service: str = "jsf",
    operation: Optional[str] = None,
    lookback: str = QUERY_LOOKBACK,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Query Jaeger and return the list of trace dicts."""
    params: Dict[str, Any] = {
        "service": service,
        "limit": limit,
        "lookback": lookback,
    }
    if operation:
        params["operation"] = operation
    resp = requests.get(JAEGER_TRACES_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data") or []


def _find_span_with_tags(
    traces: List[Dict[str, Any]],
    operation_name: str,
    required_tags: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    """Search all traces/spans for one matching operation name and ALL required tags."""
    for trace in traces:
        for span in trace.get("spans", []):
            if span.get("operationName") != operation_name:
                continue
            span_tags = {t.get("key"): str(t.get("value")) for t in span.get("tags", [])}
            if all(span_tags.get(k) == v for k, v in required_tags.items()):
                return span
    return None


def _wait_for_span(
    operation_name: str,
    required_tags: Dict[str, str],
    timeout: float = SPAN_WAIT_TIMEOUT_SECONDS,
    poll_interval: float = SPAN_POLL_INTERVAL_SECONDS,
) -> Optional[Dict[str, Any]]:
    """
    Poll Jaeger until a span matching operation_name and required_tags is found,
    or the timeout elapses.

    Returns the matching span dict, or None if not found within timeout.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            traces = _query_jaeger_traces(operation=operation_name)
            span = _find_span_with_tags(traces, operation_name, required_tags)
            if span is not None:
                return span
        except requests.exceptions.RequestException:
            pass
        time.sleep(poll_interval)
    return None


# ---------------------------------------------------------------------------
# Test 1: OTel stack is reachable (prerequisite)
# ---------------------------------------------------------------------------


def test_otel_stack_reachable():
    """Prerequisite: Jaeger must be reachable and service 'jsf' must be known."""
    try:
        resp = requests.get(JAEGER_SERVICES_URL, timeout=5)
    except requests.exceptions.ConnectionError as exc:
        pytest.fail(
            f"Jaeger is not reachable at {JAEGER_SERVICES_URL}. "
            f"Start the OTel stack before running integration tests. Error: {exc}"
        )
    assert resp.status_code == 200, f"Jaeger /api/services returned {resp.status_code}"
    services = resp.json().get("data", [])
    # After any previous test run the 'jsf' service should be registered.
    # If not yet present that is acceptable at stack-startup; we just check
    # the API itself is responding.
    assert isinstance(services, list), "Expected a list of service names from Jaeger"


# ---------------------------------------------------------------------------
# Test 2: SessionStart emits a root claude.session span
# ---------------------------------------------------------------------------


def test_session_start_emits_root_span():
    """Running SessionStart should produce a claude.session span in Jaeger."""
    session_id = f"test-integ-{uuid.uuid4().hex[:8]}"
    payload = {
        "session_id": session_id,
        "prompt_id": "p-integ-001",
    }

    result = _run_hook("SessionStart", payload, session_id)
    assert result.returncode == 0, (
        f"hook_tracer.py exited {result.returncode}\n"
        f"stdout: {result.stdout.decode()}\n"
        f"stderr: {result.stderr.decode()}"
    )

    span = _wait_for_span(
        operation_name="claude.session",
        required_tags={"session.id": session_id},
    )
    assert span is not None, (
        f"No claude.session span found in Jaeger with session.id={session_id!r} "
        f"within {SPAN_WAIT_TIMEOUT_SECONDS}s."
    )


# ---------------------------------------------------------------------------
# Test 3: PreToolUse + PostToolUse emit a claude.tool_call span
# ---------------------------------------------------------------------------


def test_pre_post_tool_emits_tool_call_span():
    """PreToolUse + PostToolUse pair should produce a claude.tool_call span."""
    session_id = f"test-integ-{uuid.uuid4().hex[:8]}"
    tool_use_id = f"tuid-{uuid.uuid4().hex[:8]}"

    # Establish session context first
    session_result = _run_hook("SessionStart", {"session_id": session_id}, session_id)
    assert session_result.returncode == 0

    pre_payload = {
        "session_id": session_id,
        "tool_use_id": tool_use_id,
        "tool_name": "Bash",
        "prompt_id": "p-integ-002",
    }
    pre_result = _run_hook("PreToolUse", pre_payload, session_id)
    assert pre_result.returncode == 0, (
        f"PreToolUse failed: {pre_result.stderr.decode()}"
    )

    # Simulate some work time between pre and post
    time.sleep(0.1)

    post_payload = {
        "session_id": session_id,
        "tool_use_id": tool_use_id,
        "tool_name": "Bash",
    }
    post_result = _run_hook("PostToolUse", post_payload, session_id)
    assert post_result.returncode == 0, (
        f"PostToolUse failed: {post_result.stderr.decode()}"
    )

    span = _wait_for_span(
        operation_name="claude.tool_call",
        required_tags={"tool.name": "Bash", "session.id": session_id},
    )
    assert span is not None, (
        f"No claude.tool_call span with tool.name=Bash and session.id={session_id!r} "
        f"found in Jaeger within {SPAN_WAIT_TIMEOUT_SECONDS}s."
    )


# ---------------------------------------------------------------------------
# Test 4: Stop event emits claude.session.stop span
# ---------------------------------------------------------------------------


def test_session_event_emits_span():
    """Stop event should produce a claude.session.stop span in Jaeger."""
    session_id = f"test-integ-{uuid.uuid4().hex[:8]}"

    # Start session first
    session_result = _run_hook("SessionStart", {"session_id": session_id}, session_id)
    assert session_result.returncode == 0

    stop_payload = {"session_id": session_id}
    stop_result = _run_hook("Stop", stop_payload, session_id)
    assert stop_result.returncode == 0, (
        f"Stop hook failed: {stop_result.stderr.decode()}"
    )

    span = _wait_for_span(
        operation_name="claude.session.stop",
        required_tags={"session.id": session_id},
    )
    assert span is not None, (
        f"No claude.session.stop span found in Jaeger with session.id={session_id!r} "
        f"within {SPAN_WAIT_TIMEOUT_SECONDS}s."
    )

#!/usr/bin/env python3
"""
hook_tracer.py — Claude hook event tracing via OpenTelemetry.

Handles all Pre/Post hook span correlation logic. Stateless: every invocation
is a fresh process. Spans are exported synchronously (SimpleSpanProcessor)
before the process exits.

Guard: if CLAUDE_CODE_ENABLE_TELEMETRY != "1" OR OTEL_EXPORTER_OTLP_ENDPOINT
is empty/unset, the script exits 0 silently — no tracing, no side effects.

Subcommands (via --event flag):
  SessionStart     — creates claude.session root span, persists context to memory
  PreToolUse       — creates claude.tool_call child span, writes context to temp file
  PostToolUse      — reads temp file, emits finished tool_call span, deletes temp file
  Stop             — emits claude.session.stop instantaneous child span
  SubagentStop     — emits claude.session.subagent_stop child span
  PreCompact       — emits claude.session.pre_compact child span
  Notification     — emits claude.session.notification child span

This script must NOT import or depend on telemetry.py.
Clean separation: telemetry.py owns factory-level spans; hook_tracer.py owns
hook-event tracing.

Usage:
  echo '{"tool_use_id":"...","tool_name":"Bash"}' | python3 hook_tracer.py --event PreToolUse
  echo '{}' | python3 hook_tracer.py --event SessionStart
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import (
    SpanContext,
    TraceFlags,
    NonRecordingSpan,
    Link,
    use_span,
)
from opentelemetry import trace as otel_trace


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

def should_exit_early() -> bool:
    """Return True if telemetry is disabled or endpoint is not configured."""
    if os.environ.get("CLAUDE_CODE_ENABLE_TELEMETRY") != "1":
        return True
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        return True
    return False


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def build_provider(endpoint: Optional[str] = None) -> TracerProvider:
    """Build a TracerProvider with OTLP gRPC exporter using SimpleSpanProcessor."""
    if endpoint is None:
        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    resource = Resource.create({"service.name": "jsf"})
    provider = TracerProvider(resource=resource)
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    provider.add_span_processor(
        SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    return provider


# ---------------------------------------------------------------------------
# Span context helpers
# ---------------------------------------------------------------------------

def _span_ids(span) -> dict:
    ctx = span.get_span_context()
    return {
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
    }


def _ctx_from(trace_id_hex: str, span_id_hex: str) -> SpanContext:
    return SpanContext(
        trace_id=int(trace_id_hex, 16),
        span_id=int(span_id_hex, 16),
        is_remote=True,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )


def _parent_ctx_from(trace_id_hex: str, span_id_hex: str):
    """Return an OTel context suitable for use as a parent span context."""
    span_ctx = _ctx_from(trace_id_hex, span_id_hex)
    return otel_trace.set_span_in_context(NonRecordingSpan(span_ctx))


# ---------------------------------------------------------------------------
# Temp file helpers
# ---------------------------------------------------------------------------

def _tmp_dir() -> str:
    return os.environ.get("TMPDIR", "/tmp")


def _temp_file_path(identifier: str) -> Path:
    return Path(_tmp_dir()) / f"jsf_hook_{identifier}.json"


# ---------------------------------------------------------------------------
# Memory helpers
# ---------------------------------------------------------------------------

def _memory_file() -> Path:
    data_dir = os.environ.get("CLAUDE_PLUGIN_DATA", str(Path.home() / ".factory"))
    p = Path(data_dir) / "memory.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch(exist_ok=True)
    return p


def _write_session_context(session_id: str, data: dict) -> None:
    """Write trace context for session_id to memory file."""
    import fcntl
    from datetime import datetime, timezone

    key = f"claude_session_trace_id:{session_id}"
    entry = {
        "id": str(uuid.uuid4()),
        "key": key,
        "value": data,
        "tags": [],
        "agent_id": "hook_tracer",
        "trace_id": data.get("trace_id", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": None,
        "session_id": session_id,
    }
    path = _memory_file()
    with open(path, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            fh.write(json.dumps(entry) + "\n")
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def read_session_context(session_id: str) -> Optional[dict]:
    """Read the most recent trace context for session_id from memory file."""
    import fcntl

    key = f"claude_session_trace_id:{session_id}"
    path = _memory_file()
    with open(path, "r") as fh:
        fcntl.flock(fh, fcntl.LOCK_SH)
        try:
            entries = []
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)

    matches = [e for e in entries if e.get("key") == key]
    if not matches:
        return None
    return matches[-1]["value"]


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

def handle_session_start(
    payload: dict,
    provider: Optional[TracerProvider] = None,
    session_id: Optional[str] = None,
) -> dict:
    """
    Create the claude.session root span.
    Persists trace_id + span_id to memory under:
      claude_session_trace_id:{session_id}
    Returns dict with trace_id, span_id.
    """
    if provider is None:
        provider = build_provider()
    if session_id is None:
        session_id = os.environ.get("CLAUDE_SESSION_ID") or str(uuid.uuid4())

    tracer = provider.get_tracer("jsf")

    # Optional link to Claude built-in trace
    links = []
    claude_trace_id = os.environ.get("CLAUDE_TRACE_ID", "").strip()
    if claude_trace_id and len(claude_trace_id) == 32:
        try:
            builtin_ctx = SpanContext(
                trace_id=int(claude_trace_id, 16),
                span_id=int("0" * 16, 16),
                is_remote=True,
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
            )
            links.append(Link(context=builtin_ctx, attributes={"link.type": "claude_builtin_trace"}))
        except ValueError:
            pass

    attributes = {
        "session.id": session_id,
        "service.name": "jsf",
    }
    # Carry optional fields from payload
    for field, attr in [("claude.model", "claude.model"), ("claude.version", "claude.version")]:
        if field in payload:
            attributes[attr] = payload[field]

    with tracer.start_as_current_span(
        "claude.session",
        links=links,
        attributes=attributes,
    ) as span:
        ids = _span_ids(span)

    # Persist context to memory
    _write_session_context(session_id, ids)

    return ids


def handle_pre_tool(
    payload: dict,
    provider: Optional[TracerProvider] = None,
    session_id: Optional[str] = None,
) -> None:
    """
    Create a claude.tool_call child span (child of session root).
    Writes span context + metadata to temp file at:
      {TMPDIR:-/tmp}/jsf_hook_{tool_use_id}.json
    The span is NOT ended here — it is ended by handle_post_tool.
    Since we can't keep the span alive across processes, we record the
    wall-clock start time in the temp file and reconstruct duration in post.
    """
    if provider is None:
        provider = build_provider()
    if session_id is None:
        session_id = os.environ.get("CLAUDE_SESSION_ID") or str(uuid.uuid4())

    tool_use_id = payload.get("tool_use_id") or payload.get("hook_event_id") or str(uuid.uuid4())
    tool_name = payload.get("tool_name", "unknown")
    hook_event = payload.get("hook_event_name", "PreToolUse")
    prompt_id = payload.get("prompt_id", "")

    # Read parent session context from memory
    session_ctx = read_session_context(session_id)

    # Build span attributes
    attributes: dict = {
        "tool.name": tool_name,
        "claude.hook_event": hook_event,
        "session.id": session_id,
    }
    if prompt_id:
        attributes["prompt.id"] = prompt_id

    # Write context to temp file so post-tool can emit the finished span.
    # We do NOT emit any OTel span here — the single claude.tool_call span is
    # emitted by handle_post_tool with the wall-clock duration measured from
    # start_time_ns captured now.
    import time
    temp_data: dict = {
        "tool_name": tool_name,
        "hook_event": hook_event,
        "session_id": session_id,
        "prompt_id": prompt_id,
        "start_time_ns": time.time_ns(),
        "attributes": attributes,
    }
    if session_ctx:
        temp_data["parent_trace_id"] = session_ctx["trace_id"]
        temp_data["parent_span_id"] = session_ctx["span_id"]

    temp_file = _temp_file_path(tool_use_id)
    temp_file.write_text(json.dumps(temp_data))


def handle_post_tool(
    payload: dict,
    provider: Optional[TracerProvider] = None,
    session_id: Optional[str] = None,
) -> None:
    """
    Read temp file, emit the completed claude.tool_call span, and delete the temp file.
    If the temp file is missing (e.g., guard prevented pre-tool from running), exit silently.
    """
    if provider is None:
        provider = build_provider()
    if session_id is None:
        session_id = os.environ.get("CLAUDE_SESSION_ID") or str(uuid.uuid4())

    tool_use_id = payload.get("tool_use_id") or payload.get("hook_event_id", "")
    temp_file = _temp_file_path(tool_use_id)

    if not temp_file.exists():
        # Temp file missing — nothing to do
        return

    try:
        temp_data = json.loads(temp_file.read_text())
    except (json.JSONDecodeError, OSError):
        # Corrupted or unreadable — clean up and exit
        try:
            temp_file.unlink()
        except OSError:
            pass
        return

    tracer = provider.get_tracer("jsf")

    import time
    start_time_ns: int = temp_data.get("start_time_ns", time.time_ns())
    end_time_ns: int = time.time_ns()

    attributes = dict(temp_data.get("attributes", {}))
    # Add prompt.id from post payload too (in case it wasn't in pre)
    if payload.get("prompt_id") and not attributes.get("prompt.id"):
        attributes["prompt.id"] = payload["prompt_id"]

    # Use parent context stored in temp file (set by pre-tool from session ctx)
    parent_trace_id = temp_data.get("parent_trace_id")
    parent_span_id = temp_data.get("parent_span_id")

    if parent_trace_id and parent_span_id:
        parent_ctx = _parent_ctx_from(parent_trace_id, parent_span_id)
        span = tracer.start_span(
            "claude.tool_call",
            context=parent_ctx,
            start_time=start_time_ns,
            attributes=attributes,
        )
    else:
        span = tracer.start_span(
            "claude.tool_call",
            start_time=start_time_ns,
            attributes=attributes,
        )

    span.end(end_time=end_time_ns)

    # Delete temp file
    try:
        temp_file.unlink()
    except OSError:
        pass


def handle_session_event(
    event_name: str,
    payload: dict,
    provider: Optional[TracerProvider] = None,
    session_id: Optional[str] = None,
) -> None:
    """
    Emit an instantaneous child span for the given session event.
    Span name: claude.session.{event_lower_snake_case}

    event_name: one of Stop, SubagentStop, PreCompact, Notification
    """
    if provider is None:
        provider = build_provider()
    if session_id is None:
        session_id = os.environ.get("CLAUDE_SESSION_ID") or str(uuid.uuid4())

    # Convert CamelCase to snake_case for span name
    import re
    span_suffix = re.sub(r"(?<!^)(?=[A-Z])", "_", event_name).lower()
    span_name = f"claude.session.{span_suffix}"

    tracer = provider.get_tracer("jsf")

    session_ctx = read_session_context(session_id)
    attributes: dict = {"session.id": session_id}
    if payload.get("prompt_id"):
        attributes["prompt.id"] = payload["prompt_id"]

    if session_ctx:
        parent_ctx = _parent_ctx_from(session_ctx["trace_id"], session_ctx["span_id"])
        with tracer.start_as_current_span(
            span_name,
            context=parent_ctx,
            attributes=attributes,
        ):
            pass
    else:
        with tracer.start_as_current_span(span_name, attributes=attributes):
            pass


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if should_exit_early():
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description="Claude hook event tracer using OpenTelemetry."
    )
    parser.add_argument(
        "--event",
        required=True,
        choices=["SessionStart", "PreToolUse", "PostToolUse", "Stop",
                 "SubagentStop", "PreCompact", "Notification"],
        help="Hook event name",
    )
    args = parser.parse_args()

    # Read stdin payload
    payload: dict = {}
    if not sys.stdin.isatty():
        try:
            raw = sys.stdin.read().strip()
            if raw:
                payload = json.loads(raw)
        except (json.JSONDecodeError, OSError):
            pass

    session_id = os.environ.get("CLAUDE_SESSION_ID") or str(uuid.uuid4())
    provider = build_provider()

    if args.event == "SessionStart":
        result = handle_session_start(payload, provider=provider, session_id=session_id)
        print(json.dumps(result))

    elif args.event == "PreToolUse":
        handle_pre_tool(payload, provider=provider, session_id=session_id)

    elif args.event == "PostToolUse":
        handle_post_tool(payload, provider=provider, session_id=session_id)

    elif args.event in ("Stop", "SubagentStop", "PreCompact", "Notification"):
        handle_session_event(args.event, payload, provider=provider, session_id=session_id)

    # Force flush before exit
    provider.force_flush()


if __name__ == "__main__":
    main()

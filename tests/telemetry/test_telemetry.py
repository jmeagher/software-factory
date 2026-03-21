import subprocess, json, os
from pathlib import Path

# Run from repo root: python3 -m pytest tests/telemetry/test_telemetry.py -v
SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "telemetry.py"

def run(args, env=None):
    # SF_OTEL_ENABLED=0 disables OTLP export; span IDs are still generated and returned
    e = {**os.environ, **(env or {}), "SF_OTEL_ENABLED": "0"}
    return subprocess.run(["python3", str(SCRIPT)] + args, capture_output=True, text=True, env=e)

def test_start_root_returns_ids():
    r = run(["start-root", "--task", "test-task"])
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert "trace_id" in data and len(data["trace_id"]) == 32
    assert "span_id" in data and len(data["span_id"]) == 16

def test_start_root_is_stateless():
    """Two separate calls produce different span IDs (each invocation is a fresh span)."""
    r1 = run(["start-root", "--task", "task-a"])
    r2 = run(["start-root", "--task", "task-b"])
    d1, d2 = json.loads(r1.stdout), json.loads(r2.stdout)
    assert d1["span_id"] != d2["span_id"]
    assert d1["trace_id"] != d2["trace_id"]

def test_start_phase_returns_new_trace_id():
    r = run(["start-root", "--task", "test-task"])
    root = json.loads(r.stdout)
    r2 = run(["start-phase", "--phase", "planning",
               "--root-trace-id", root["trace_id"],
               "--root-span-id", root["span_id"]])
    assert r2.returncode == 0, r2.stderr
    phase = json.loads(r2.stdout)
    # Phase must have a DIFFERENT trace_id from root (independent trace)
    assert phase["trace_id"] != root["trace_id"]
    assert "span_id" in phase

def test_phase_link_points_to_root():
    """Phase span output includes the root trace_id it was linked to."""
    r = run(["start-root", "--task", "t"])
    root = json.loads(r.stdout)
    r2 = run(["start-phase", "--phase", "impl",
               "--root-trace-id", root["trace_id"],
               "--root-span-id", root["span_id"]])
    phase = json.loads(r2.stdout)
    assert phase["linked_root_trace_id"] == root["trace_id"]

def test_emit_forward_link():
    """emit-forward-link creates an instantaneous span in root trace context with child trace_id."""
    r = run(["start-root", "--task", "t"])
    root = json.loads(r.stdout)
    r2 = run(["start-phase", "--phase", "impl",
               "--root-trace-id", root["trace_id"],
               "--root-span-id", root["span_id"]])
    phase = json.loads(r2.stdout)
    r3 = run(["emit-forward-link",
               "--root-trace-id", root["trace_id"],
               "--root-span-id", root["span_id"],
               "--child-trace-id", phase["trace_id"],
               "--child-span-id", phase["span_id"],
               "--phase", "impl"])
    assert r3.returncode == 0
    result = json.loads(r3.stdout)
    assert result["span_name"] == "factory.phase_started"
    assert result["child_trace_id"] == phase["trace_id"]

def test_emit_event():
    r = run(["emit-event",
             "--trace-id", "a" * 32, "--parent-span-id", "b" * 16,
             "--name", "factory.validation", "--attrs", '{"result":"pass"}'])
    assert r.returncode == 0
    result = json.loads(r.stdout)
    assert result["span_name"] == "factory.validation"

def test_otel_disabled_still_returns_ids():
    """With SF_OTEL_ENABLED=0, no export happens but IDs are still valid."""
    r = run(["start-root", "--task", "no-export"], {"SF_OTEL_ENABLED": "0"})
    data = json.loads(r.stdout)
    assert len(data["trace_id"]) == 32

---
name: jsf-otel-tracing
description: Software factory OpenTelemetry tracing — use when emitting traces for factory work. Covers root trace, phase sub-traces, and bi-directional linking.
version: 0.1.0
---

# OpenTelemetry Tracing

## Overview

Factory work emits OTLP traces to `http://localhost:4317` (configurable via `OTEL_EXPORTER_OTLP_ENDPOINT`).

Set `SF_OTEL_ENABLED=0` to disable export without breaking anything (useful in tests).

## Trace Architecture

- **Root trace**: one per factory task. Spans the full workflow. Stored in memory as `main_trace_id` + `main_span_id`.
- **Phase sub-traces**: one independent trace per phase. Links back to root (phase → root via OTel Link). Root logs child trace IDs as events (`factory.phase_started`) for forward traceability (root → phase).

## Stateless Design

Every `telemetry.py` call is a fresh process. Each command creates an instantaneous span, ends it, and exports it before exit (using `SimpleSpanProcessor`). No state is held in memory between calls. Returned IDs are stored in `memory.py` for cross-call correlation.

## Orchestrator Protocol

```bash
# At task start: emit root span, store IDs
ROOT=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/telemetry.py" start-root --task "feature-name")
ROOT_TRACE=$(echo "$ROOT" | python3 -c "import sys,json; print(json.load(sys.stdin)['trace_id'])")
ROOT_SPAN=$(echo "$ROOT" | python3 -c "import sys,json; print(json.load(sys.stdin)['span_id'])")
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write --key main_trace_id --value "\"${ROOT_TRACE}\""
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write --key main_span_id --value "\"${ROOT_SPAN}\""

# When starting a phase: emit phase span (independent trace, links back to root)
PHASE=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/telemetry.py" start-phase \
  --phase "planning" --root-trace-id "${ROOT_TRACE}" --root-span-id "${ROOT_SPAN}")
PHASE_TRACE=$(echo "$PHASE" | python3 -c "import sys,json; print(json.load(sys.stdin)['trace_id'])")
PHASE_SPAN=$(echo "$PHASE" | python3 -c "import sys,json; print(json.load(sys.stdin)['span_id'])")

# Emit forward link: instantaneous span in root trace recording child trace_id (root → phase)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/telemetry.py" emit-forward-link \
  --root-trace-id "${ROOT_TRACE}" --root-span-id "${ROOT_SPAN}" \
  --child-trace-id "${PHASE_TRACE}" --child-span-id "${PHASE_SPAN}" --phase "planning"

# Store phase context in memory
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write --key "phase_trace:planning" --value "\"${PHASE_TRACE}\""
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write --key "phase_span:planning" --value "\"${PHASE_SPAN}\""

# Emit a discrete factory event within a trace
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/telemetry.py" emit-event \
  --trace-id "${PHASE_TRACE}" --parent-span-id "${PHASE_SPAN}" \
  --name "factory.validation" --attrs '{"result":"pass","tests_run":42}'
```

## Key Span Names

| Span | When |
|------|------|
| `factory.task` | Full workflow duration (root trace) |
| `factory.phase` | Each implementation phase (sub-trace) |
| `factory.validation.automated` | After running test suite |
| `factory.validation.manual` | After user manual confirmation |
| `factory.checkpoint` | After git commit checkpoint |

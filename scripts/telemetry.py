#!/usr/bin/env python3
"""
OTel span management for jsf. Stateless CLI — every invocation is a fresh process.
Each command creates an instantaneous "event span", ends it, and flushes before exiting.
Span IDs returned in stdout should be stored in memory.py for cross-call correlation.

Usage:
  telemetry.py start-root       --task NAME
  telemetry.py start-phase      --phase NAME --root-trace-id TID --root-span-id SID
  telemetry.py emit-forward-link --root-trace-id TID --root-span-id SID \
                                  --child-trace-id TID2 --child-span-id SID2 --phase NAME
  telemetry.py emit-event       --trace-id TID --parent-span-id SID --name NAME [--attrs JSON]

Bi-directional linking:
  phase → root: phase span includes an OTel Link to the root span at creation (start-phase)
  root → phase: emit-forward-link creates an instantaneous span IN the root trace context
                with the child trace_id as an attribute — visible in any trace viewer that
                follows the root trace_id

Set SF_OTEL_ENABLED=0 to disable OTLP export (tests/dry-run). IDs are still generated.
"""
import argparse, json, os, sys
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import SpanContext, TraceFlags, NonRecordingSpan, Link, StatusCode, use_span
from opentelemetry import context as otel_context, trace as otel_trace

ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
ENABLED = os.environ.get("SF_OTEL_ENABLED", "1") != "0"


def _make_provider(resource_attrs: dict) -> TracerProvider:
    resource = Resource.create({"service.name": "jsf", "service.version": "0.1.0",
                                **resource_attrs})
    provider = TracerProvider(resource=resource)
    if ENABLED:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        # SimpleSpanProcessor: exports each span synchronously before process exits
        provider.add_span_processor(SimpleSpanProcessor(
            OTLPSpanExporter(endpoint=ENDPOINT, insecure=True)
        ))
    return provider


def _ctx_from(trace_id_hex: str, span_id_hex: str) -> SpanContext:
    return SpanContext(
        trace_id=int(trace_id_hex, 16),
        span_id=int(span_id_hex, 16),
        is_remote=True,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )


def _span_ids(span) -> dict:
    ctx = span.get_span_context()
    return {"trace_id": format(ctx.trace_id, "032x"), "span_id": format(ctx.span_id, "016x")}


def cmd_start_root(args):
    """Emits a root 'factory.task' span. Returns trace_id and span_id for storage in memory."""
    provider = _make_provider({"factory.task": args.task})
    tracer = provider.get_tracer("jsf")
    # No parent = new TraceID
    with tracer.start_as_current_span("factory.task",
                                      attributes={"factory.task.name": args.task}) as span:
        ids = _span_ids(span)
    # Span is ended on __exit__; SimpleSpanProcessor exports it synchronously
    print(json.dumps(ids))


def cmd_start_phase(args):
    """
    Emits a 'factory.phase' span in a NEW independent trace, with an OTel Link to root (phase → root).
    Returns the new trace_id + span_id. Store in memory for emit-forward-link.
    """
    provider = _make_provider({"factory.phase": args.phase})
    tracer = provider.get_tracer("jsf")
    root_link = Link(
        context=_ctx_from(args.root_trace_id, args.root_span_id),
        attributes={"link.type": "root_trace", "factory.phase.name": args.phase}
    )
    # start_span with no parent context = generates a new TraceID (independent trace)
    with tracer.start_as_current_span("factory.phase", links=[root_link],
                                      attributes={"factory.phase.name": args.phase}) as span:
        ids = _span_ids(span)
    print(json.dumps({**ids, "linked_root_trace_id": args.root_trace_id}))


def cmd_emit_forward_link(args):
    """
    Emits an instantaneous 'factory.phase_started' span WITHIN the root trace (using root
    trace_id + root span_id as the parent context). This records the child trace_id as an
    attribute visible when browsing the root trace — completing the bi-directional link.
    """
    provider = _make_provider({"factory.task": "link-recorder"})
    tracer = provider.get_tracer("jsf")
    root_ctx = _ctx_from(args.root_trace_id, args.root_span_id)
    # Use the root span context as parent so this span appears inside the root trace
    parent_ctx = otel_trace.set_span_in_context(NonRecordingSpan(root_ctx))
    with tracer.start_as_current_span(
        "factory.phase_started",
        context=parent_ctx,
        attributes={
            "factory.phase.name": args.phase,
            "link.child_trace_id": args.child_trace_id,
            "link.child_span_id": args.child_span_id,
            "link.type": "child_phase",
        }
    ) as span:
        ids = _span_ids(span)
    print(json.dumps({"span_name": "factory.phase_started",
                      "child_trace_id": args.child_trace_id, **ids}))


def cmd_emit_event(args):
    """
    Emits an instantaneous named span within an existing trace context.
    Use for checkpoints, validation results, and other discrete factory events.
    """
    provider = _make_provider({"factory.event": args.name})
    tracer = provider.get_tracer("jsf")
    parent_ctx_obj = _ctx_from(args.trace_id, args.parent_span_id)
    parent_ctx = otel_trace.set_span_in_context(NonRecordingSpan(parent_ctx_obj))
    attrs = json.loads(args.attrs) if args.attrs else {}
    with tracer.start_as_current_span(args.name, context=parent_ctx,
                                      attributes=attrs) as span:
        ids = _span_ids(span)
    print(json.dumps({"span_name": args.name, **ids}))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")

    sr = sub.add_parser("start-root"); sr.add_argument("--task", required=True)

    sp = sub.add_parser("start-phase")
    sp.add_argument("--phase", required=True)
    sp.add_argument("--root-trace-id", required=True)
    sp.add_argument("--root-span-id", required=True)

    fl = sub.add_parser("emit-forward-link")
    fl.add_argument("--root-trace-id", required=True)
    fl.add_argument("--root-span-id", required=True)
    fl.add_argument("--child-trace-id", required=True)
    fl.add_argument("--child-span-id", required=True)
    fl.add_argument("--phase", required=True)

    ev = sub.add_parser("emit-event")
    ev.add_argument("--trace-id", required=True)
    ev.add_argument("--parent-span-id", required=True)
    ev.add_argument("--name", required=True)
    ev.add_argument("--attrs")

    args = p.parse_args()
    dispatch = {
        "start-root": cmd_start_root, "start-phase": cmd_start_phase,
        "emit-forward-link": cmd_emit_forward_link, "emit-event": cmd_emit_event,
    }
    if args.cmd in dispatch:
        dispatch[args.cmd](args)
    else:
        p.print_help(); sys.exit(1)


if __name__ == "__main__":
    main()

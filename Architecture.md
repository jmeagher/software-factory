# Architecture: John's Software Factory (jsf)

## Overview

John's Software Factory (`jsf`) is a Claude Code plugin that implements a structured, multi-agent software development workflow. It orchestrates a repeatable cycle of clarification, technical planning, TDD-driven implementation, security review, and validation — all coordinated through shared memory and OpenTelemetry tracing.

The plugin integrates with Claude Code's plugin system: skills define reusable behavioral protocols, agents are specialized subagents dispatched by the orchestrator, commands expose workflow entry points to the user, rules enforce coding standards, hooks guard against dangerous shell and database operations, and scripts provide shared infrastructure.

---

## Plugin Manifest (`plugin.json`)

The plugin manifest is located at the repo root. It is not present as a standalone file in this repository; the plugin is registered via the plugin cache at `~/.claude/plugins/cache/jsf/jsf/0.1.0/`. Key fields:

- **name**: `jsf`
- **version**: `0.1.0`
- **author**: John Meagher

---

## Skills (7 total)

Skills are Markdown documents that define behavioral protocols for agents. Each skill is loaded by reference when an agent or command invokes it.

| Skill | File | Purpose |
|-------|------|---------|
| `clarification` | `skills/clarification/SKILL.md` | Runs a structured Q&A dialogue to gather all requirements before planning begins. Produces a confirmed Clarification Summary written to memory. |
| `memory-protocol` | `skills/memory-protocol/SKILL.md` | Defines how agents read and write shared state via `scripts/memory.py`. Documents well-known memory keys and the agent startup protocol every agent must follow. |
| `otel-tracing` | `skills/otel-tracing/SKILL.md` | Describes how to emit OpenTelemetry traces for factory work, including root traces, per-phase sub-traces, and bi-directional linking between them. |
| `spec-planning` | `skills/spec-planning/SKILL.md` | Guides production of a technical spec (problem, architecture, data model, API surface, security) and a phased implementation plan after clarification is confirmed. |
| `tdd-implementation` | `skills/tdd-implementation/SKILL.md` | Enforces red-green TDD discipline: write a failing test, confirm failure, implement minimum code to pass, confirm pass — before committing any phase. |
| `validation-gate` | `skills/validation-gate/SKILL.md` | Defines phase completion criteria: automated tests must pass, and manual validation must be explicitly confirmed by the user if the phase touches UI, APIs, or external integrations. |
| `workflow` | `skills/workflow/SKILL.md` | The master orchestration protocol. Defines the full factory lifecycle (intake → clarification → spec/plan → implementation phases → done), config layering, parallelization rules, and context discipline. |

---

## Agents (5 total)

Agents are subagent definitions dispatched by the orchestrator using the Claude Code `Agent` tool. Each agent follows one or more skills and writes its outcome to memory. The orchestrator dispatches agents using the `subagent_type` field shown below.

| Agent | File | Role | Skill | Dispatch String |
|-------|------|------|-------|-----------------|
| `clarifier` | `agents/clarifier.md` | Conducts the structured clarification dialogue with the user; writes `clarification_summary` to memory. | `clarification` | `jsf:clarifier` |
| `planner` | `agents/planner.md` | Reads `clarification_summary`, produces the technical spec and phased implementation plan, and writes both to memory after user confirmation. | `spec-planning` | `jsf:planner` |
| `implementer` | `agents/implementer.md` | Implements a single phase using TDD discipline; reads its assignment from `agent_context` in memory and writes `phase_complete:<phase_name>` when done. | `tdd-implementation` | `jsf:implementer` |
| `reviewer` | `agents/reviewer.md` | Reviews all code changes since the last commit for hardcoded secrets, SQL injection, shell injection, and insecure defaults; writes `review_result:<phase_name>` to memory. | `tdd-implementation` (code standards section) | `jsf:reviewer` |
| `validator` | `agents/validator.md` | Runs the phase test suite, checks whether manual validation is required, prompts the user if so, and writes `validation_confirmed:<phase_name>` to memory when both criteria are met. | `validation-gate` | `jsf:validator` |

---

## Commands (4 total)

Commands are user-facing slash commands that serve as workflow entry points. They are invoked directly in the Claude Code conversation.

| Command | File | What It Does |
|---------|------|--------------|
| `start` | `commands/start.md` | Begins a new factory workflow. Accepts an optional request argument, writes it to memory as `initial_request`, runs memory garbage collection, then dispatches the clarifier agent. |
| `resume` | `commands/resume.md` | Resumes an in-progress workflow from the last memory checkpoint. Reads all live memory keys, identifies the most recent incomplete phase, shows the user current state, and asks for confirmation before continuing. |
| `status` | `commands/status.md` | Displays the current factory state: project request, clarification status, plan phases, per-phase completion status with commit SHAs, pending validations, and memory file statistics. |
| `validate` | `commands/validate.md` | Dispatches the validator agent for the current in-progress phase, running automated tests and coordinating manual validation if required by the phase spec. |

---

## Rules

The `rules/` directory contains `.mdc` files that are Cursor-compatible rule documents. These enforce coding standards and workflow protocols at the editor/AI level.

Rule files in this directory:

- `jsf-clarification.mdc`
- `jsf-memory-protocol.mdc`
- `jsf-otel-tracing.mdc`
- `jsf-spec-planning.mdc`
- `jsf-tdd-implementation.mdc`
- `jsf-validation-gate.mdc`
- `jsf-workflow.mdc`

**Why the `jsf-` prefix on rule files:** Rule files are NOT namespaced by Claude Code's plugin system the way skills, agents, and commands are. When the plugin system loads a skill named `workflow`, it is accessed as `jsf:workflow` — the `jsf` namespace is added automatically. Rule files, however, are plain `.mdc` files loaded directly by Cursor or similar tools without any plugin namespacing. To avoid name collisions with rules from other sources, they retain the explicit `jsf-` prefix in their filenames.

---

## Hooks

`hooks/hooks.json` registers hooks for all seven Claude Code hook events. Safety hooks block dangerous shell and database operations. Tracing hooks (all `async: true`) emit OpenTelemetry spans via `scripts/hook_tracer.py` gated on `CLAUDE_CODE_ENABLE_TELEMETRY=1`.

| Event | Handler | Purpose |
|-------|---------|---------|
| `SessionStart` | `hook_tracer.py --event SessionStart` | Opens `claude.session` root span |
| `PreToolUse` (Bash) | `block-dangerous-bash.sh`, `block-dangerous-git.sh`, `block-dangerous-sql.sh` | Safety blocking (synchronous) |
| `PreToolUse` (all) | `hook_tracer.py --event PreToolUse` | Starts `claude.tool_call` span; writes temp file for Pre/Post correlation |
| `PostToolUse` (all) | `hook_tracer.py --event PostToolUse` | Closes `claude.tool_call` span; reads and deletes temp file |
| `Stop` | `hook_tracer.py --event Stop` | Emits `claude.session.stop` span |
| `SubagentStop` | `hook_tracer.py --event SubagentStop` | Emits `claude.session.subagent_stop` span |
| `PreCompact` | `hook_tracer.py --event PreCompact` | Emits `claude.session.compact` span |
| `Notification` | `hook_tracer.py --event Notification` | Emits `claude.session.notification` span |

### Hook Scripts (`hooks/scripts/`)

**`block-dangerous-bash.sh`** — Blocks destructive shell patterns:
- `rm -rf` and variants
- `find ... -delete` and `find ... -exec rm`
- `dd` writing to raw block devices
- `mkfs.*` (filesystem formatting)
- Fork bombs (`: () { : | : }; :`)

**`block-dangerous-git.sh`** — Blocks dangerous git operations:
- `git push --force` / `-f` without `--force-with-lease`
- `git reset --hard`
- `git checkout -- .` (discards all working changes)
- `git clean -fd` (deletes untracked files)

**`block-dangerous-sql.sh`** — Blocks dangerous SQL when using database CLIs (`psql`, `mysql`, `sqlite3`, `sqlplus`, `pgcli`):
- `DROP TABLE`, `DROP DATABASE`, `DROP SCHEMA`
- `TRUNCATE`
- `DELETE FROM` without a `WHERE` clause
- `UPDATE ... SET` without a `WHERE` clause

---

## Scripts

All three scripts live in `scripts/` and are invoked via Bash by agents, the orchestrator, and hook runners.

**`memory.py`** — Shared state store for all factory agents. Reads and writes a JSONL file at `${CLAUDE_PLUGIN_DATA}/memory.jsonl`, which persists across sessions. Supports operations: `write`, `read`, `query`, `list-keys`, `delete`, `gc`. All inter-agent coordination (clarification summaries, implementation plans, phase completion signals, review results, validation confirmations) flows through this file.

**`telemetry.py`** — OpenTelemetry tracing client for factory-level spans. Each invocation is a fresh process that creates one span, ends it, and exports it via OTLP to `OTEL_EXPORTER_OTLP_ENDPOINT` (default: `http://localhost:4317`). Supports `start-root`, `start-phase`, `emit-forward-link`, and `emit-event` subcommands. When `CLAUDE_CODE_ENABLE_TELEMETRY=1` and `CLAUDE_SESSION_ID` are set, factory spans include an OTel Link back to the `claude.session` root span emitted by `hook_tracer.py`, connecting factory traces to the session trace in Jaeger. Gated on `CLAUDE_CODE_ENABLE_TELEMETRY=1`.

**`hook_tracer.py`** — OpenTelemetry tracing client for Claude hook events. Invoked by all seven hook entries in `hooks/hooks.json`. Each invocation is a stateless process that emits one span and exports it before exiting (`SimpleSpanProcessor`). Pre/Post tool-call correlation uses a temp file keyed by `tool_use_id` at `${TMPDIR:-/tmp}/jsf_hook_{tool_use_id}.json`. Session root span context (trace ID + span ID) is stored in `memory.py` under `claude_session_trace_id:{session_id}` so child spans from later hook invocations can reference the correct parent. Gated on `CLAUDE_CODE_ENABLE_TELEMETRY=1` and a non-empty `OTEL_EXPORTER_OTLP_ENDPOINT`.

---

## Tests

Tests live in `tests/` with the following layout:

```
tests/
  memory/
    test_memory.py                    # Unit tests for memory.py operations
  telemetry/
    test_telemetry.py                 # Unit tests for telemetry.py span emission
    test_telemetry_session_link.py    # Tests for factory→session OTel Link
  hook_tracer/
    test_hook_tracer.py               # 25 unit tests for hook_tracer.py (in-memory OTel exporter, no live stack)
  integration/
    test_otel_integration.py          # 4 black-box tests: verifies spans land in Jaeger via HTTP API
                                      # Skipped if CLAUDE_CODE_ENABLE_TELEMETRY or OTEL_EXPORTER_OTLP_ENDPOINT unset
  evals/
    skills/
      test_clarification.py
      test_memory_protocol.py
      test_otel_tracing.py
      test_spec_planning.py
      test_tdd_implementation.py
      test_validation_gate.py
      test_workflow.py
    commands/
      test_resume.py
      test_start.py
      test_status.py
    hooks/
      test_hook_script_paths.py
      test_hooks_json_structure.py
  hooks/
    test-dangerous-bash.sh            # Shell-level tests for bash hook script
    test-dangerous-git.sh             # Shell-level tests for git hook script
    test-dangerous-sql.sh             # Shell-level tests for SQL hook script
  test_hooks_json_otel_events.py      # 43 structural tests: all 7 hook events wired to hook_tracer.py
  test_infrastructure.py              # Infrastructure sanity checks
  conftest.py                         # otel_configured fixture; integration marker registration
  run-all.sh                          # Runs all test suites
```

Run targets (via `Makefile`):

| Target | What runs |
|--------|-----------|
| `make test` | Full suite — unit + integration (integration skips if OTel not configured) |
| `make test-unit` | `tests/hook_tracer/` and `tests/telemetry/` only — no external dependencies |
| `make test-integration` | `tests/integration/` only — requires live OTel stack |

The `evals/` subtree contains behavioral evaluation tests that verify skill documents, command definitions, and hook configurations have correct structure and content — not just that the Python code runs, but that the factory's instructional content is coherent.

---

## Naming Convention

Within the `jsf` plugin namespace, component names do **not** repeat the `jsf-` prefix.

- Skills: `workflow`, `clarification`, `tdd-implementation` (not `jsf-workflow`)
- Agents: `clarifier`, `planner`, `implementer`, `reviewer`, `validator` (not `jsf-clarifier`)
- Commands: `start`, `resume`, `status`, `validate` (not `jsf-start`)

When dispatching an agent, the plugin namespace is prepended by the caller: `jsf:clarifier`, `jsf:implementer`, etc. This means a component named `clarifier` is correctly dispatched as `jsf:clarifier` — never as `jsf:jsf-clarifier`.

**Rule files are the exception.** Because `.mdc` rule files are not namespaced by the plugin system, they carry the explicit `jsf-` prefix in their filenames to avoid collisions: `jsf-workflow.mdc`, `jsf-tdd-implementation.mdc`, etc.

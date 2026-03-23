# John's Software Factory (JSF)

An intelligent, phased workflow plugin for Claude Code that takes software projects from initial idea through complete, validated implementation. JSF enforces test-driven development discipline, security review gates, and structured human validation checkpoints — so you ship code that works and is safe.

## Philosophy

- **Simple over clever**: JSF builds only what you ask for, with no speculative features or premature abstractions
- **Safety by default**: hooks block dangerous shell, git, and SQL commands before they execute
- **Validated progress**: each phase must pass automated tests and (when required) manual review before proceeding
- **Persistent state**: work survives interruptions via a file-based memory system; resume where you left off

---

## Getting Started

### Installation via Plugin Marketplace

1. Open Claude Code and navigate to **Settings → Plugins → Marketplace**
2. Search for **"jsf"** or **"John's Software Factory"**
3. Click **Install**

That's it. No additional setup is required for basic use.

### Optional: OpenTelemetry Tracing

JSF can emit spans to any OTLP-compatible collector (Jaeger, Grafana Tempo, etc.) for observability into long-running factory sessions.

Set the endpoint before starting Claude Code:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export SF_OTEL_ENABLED=1
```

The defaults (`localhost:4317`, enabled) are set automatically by the plugin's session-start hook if you don't override them.

### Python Dependencies (for memory and telemetry scripts)

```bash
pip install -r path/to/jsf-plugin/scripts/requirements.txt
```

### Basic Use

Once installed, start a new project session with:

```
/jsf:start I want to build a REST API for managing book reviews
```

JSF will guide you through a structured clarification dialogue, generate a technical spec and phased implementation plan, implement each phase with TDD discipline, and validate each phase before moving on. You can check progress, pause, and resume at any time.

---

## Commands

Commands are invoked with the `/jsf:` prefix in Claude Code.

### `/jsf:start [description]`

Starts a new software factory workflow. Provide an optional description of what you want to build; if omitted, JSF will ask.

**What it does:**
1. Writes an initial memory checkpoint
2. Launches the clarification dialogue (scope, success criteria, tech stack, constraints)
3. Confirms your answers before proceeding to planning

**Example:**
```
/jsf:start Add webhook support to the existing notifications service
```

---

### `/jsf:status`

Displays the current state of the active factory workflow.

**Shows:**
- Project summary and clarification status
- All planned phases with completion indicators
- Any pending validations waiting on manual review
- Memory key count (for debugging multi-agent state)

**Example:**
```
/jsf:status
```

Sample output:
```
Project: Book Review REST API
Clarification: confirmed
Plan: 5 phases

  [✓] Phase 1: Database schema + migrations
  [✓] Phase 2: Core CRUD endpoints
  [→] Phase 3: Authentication middleware  ← current
  [ ] Phase 4: Rate limiting
  [ ] Phase 5: Integration tests + docs

Pending validations: none
```

---

### `/jsf:validate`

Runs the validation gate for the current phase. Executes automated tests and, when required, coordinates manual review.

Manual review is triggered when a phase touches UI changes, API surface changes, external integrations, or any project-specific rules defined during clarification.

**Example:**
```
/jsf:validate
```

A phase only advances when both automated tests pass **and** all required manual confirmations are given.

---

### `/jsf:resume`

Resumes a factory workflow from the last memory checkpoint. Use this when returning to a project after a break or after a Claude Code session ends.

**What it does:**
1. Reads the persisted memory state
2. Shows which phases are complete and which is next
3. Picks up implementation from where it left off

**Example:**
```
/jsf:resume
```

---

## Skills

Skills are the internal building blocks JSF uses. You don't invoke these directly in normal use — commands orchestrate them automatically. Understanding them helps you know what's happening under the hood and how to customize or extend the workflow.

### `workflow`

The master orchestrator. Controls the full lifecycle: intake → clarification → spec+plan → phased TDD implementation → validation → completion. All other skills are invoked through this one.

### `clarification`

Runs a structured Q&A dialogue covering:
- Scope and what is explicitly **out** of scope
- Success criteria (how you'll know it's done)
- Tech stack and any hard constraints
- CI/CD assumptions already in place
- Whether any UI, API, or external integration changes require manual validation
- Constraints around existing code to preserve

Produces a `clarification_summary` stored in memory that all downstream agents read.

### `spec-planning`

Converts the confirmed clarification summary into:
- A technical specification (problem statement, architecture, data model, API surface, security considerations)
- An ordered list of implementation phases, each with: test files to write first, source files to create/modify, and whether phases can run in parallel

### `tdd-implementation`

Implements a single phase with strict red-green-refactor discipline:
1. Write failing tests first
2. Write the minimum code to make them pass
3. Refactor if needed
4. Security review before committing: checks for hardcoded credentials, SQL/shell/XSS injection, insecure defaults, missing input validation

### `validation-gate`

After implementation, validates phase completion:
- Runs the full automated test suite
- Checks which manual validation triggers fire (UI changes, API changes, external integrations)
- Presents a checklist for human confirmation when required
- Only marks a phase complete when all checks pass

### `memory-protocol`

Manages persistent JSONL memory with file-based locking for safe multi-agent coordination. Stores and retrieves:
- `clarification_summary` — confirmed answers from the clarification dialogue
- `implementation_plan` — the full phase list
- `phase_complete:<name>` — per-phase completion records
- `review_result`, `validation_confirmed` — review and validation outcomes
- `checkpoints` — git SHAs at each phase boundary

### `otel-tracing`

Emits OpenTelemetry spans for factory activity monitoring. Spans cover the full workflow (`factory.task`), individual phases (`factory.phase`), automated validation (`factory.validation.automated`), manual validation (`factory.validation.manual`), and memory checkpoints (`factory.checkpoint`). Useful for understanding where time is spent in long multi-phase projects.

---

## Safety Hooks

JSF installs three pre-tool hooks that block dangerous operations before they execute:

| Hook | What it blocks |
|------|----------------|
| `block-dangerous-bash.sh` | `rm -rf`, force operations, process kills |
| `block-dangerous-git.sh` | Force push, `reset --hard`, `checkout .` |
| `block-dangerous-sql.sh` | `DROP TABLE`, `DELETE` without a `WHERE` clause |

These run automatically on every Bash tool call. No configuration needed.

---

## Example Workflows

### 1. Greenfield REST API

You have an idea. Nothing exists yet.

```
/jsf:start Build a REST API for managing a book review collection. PostgreSQL backend, FastAPI, JWT auth.
```

JSF asks clarifying questions: What endpoints? Admin vs. public access? Any existing schema to preserve? Rate limiting? What counts as "done"?

After you confirm the answers, JSF produces a 5-phase plan:
1. Schema + migrations
2. CRUD endpoints (unauthenticated)
3. JWT auth middleware
4. Rate limiting
5. Integration tests + OpenAPI docs

It implements phase 1 with TDD (writes schema tests first, then the migration), runs `/jsf:validate`, gets your confirmation that the schema looks correct, then moves to phase 2. Repeat through all 5 phases. At the end you have tested, reviewed, committed code at each phase boundary.

---

### 2. Adding a Feature to an Existing Service

You have an existing notifications service and want to add webhook support.

```
/jsf:start Add webhook support to the notifications service. Webhooks should fire on new notification events. HMAC-SHA256 signing. Retry on failure with exponential backoff.
```

During clarification, JSF asks: Which notification event types? Where is the retry state stored? Any existing webhook tables? Is the signing key per-tenant or global?

The plan JSF produces respects your existing codebase. It reads relevant files before writing any code, avoids touching code outside the webhook feature, and flags the new API surface (webhook registration endpoints) as requiring manual validation.

After phase 2 (the new endpoints), `/jsf:validate` pauses for manual review: "New API endpoints added — please verify the registration flow behaves as expected." You test it, confirm, and JSF proceeds.

---

### 3. Resuming After an Interruption

You started a project yesterday, got through 3 of 5 phases, and your session ended.

```
/jsf:resume
```

JSF reads its memory, shows you:
```
Completed: Phase 1 (schema), Phase 2 (CRUD), Phase 3 (auth)
Next: Phase 4 — Rate limiting
```

It picks up exactly where it left off. No re-explaining the project. No re-running completed phases. The git SHA from the phase 3 checkpoint is recorded so you can diff what's been done.

---

### 4. Checking In Mid-Session

You're partway through a multi-phase build and want a quick status check.

```
/jsf:status
```

Output:
```
Project: Webhook support for notifications service
Clarification: confirmed (8 keys)
Plan: 4 phases

  [✓] Phase 1: Webhook table + migration
  [✓] Phase 2: Registration + delivery endpoints
  [→] Phase 3: HMAC signing + retry logic  ← implementing now
  [ ] Phase 4: End-to-end integration tests

Pending validations: none
```

Everything is visible at a glance. When phase 3 finishes, you run `/jsf:validate` to advance to phase 4.

---

## Repository Structure

```
.
├── .claude-plugin/
│   ├── plugin.json          # Claude Code plugin manifest
│   └── marketplace.json     # Marketplace listing metadata
├── .cursor-plugin/
│   └── plugin.json          # Cursor plugin manifest
├── commands/
│   ├── start.md             # /jsf:start command
│   ├── resume.md            # /jsf:resume command
│   ├── status.md            # /jsf:status command
│   └── validate.md          # /jsf:validate command
├── skills/
│   ├── workflow/        # Master orchestration skill
│   ├── clarification/   # Structured Q&A skill
│   ├── spec-planning/   # Spec + plan generation skill
│   ├── tdd-implementation/ # TDD implementation skill
│   ├── validation-gate/ # Phase validation skill
│   ├── memory-protocol/ # Persistent memory skill
│   └── otel-tracing/   # OpenTelemetry tracing skill
├── agents/                  # Specialist agent definitions
├── hooks/
│   ├── hooks.json           # Hook configuration
│   └── scripts/             # Safety hook shell scripts
├── scripts/
│   ├── memory.py            # JSONL memory manager
│   └── telemetry.py         # OTel span emitter
├── rules/                   # Cursor-compatible rule files
├── docs/
│   └── ProjectGoals.md      # Design goals and requirements
└── tests/                   # Plugin test suite
```

---

## License

MIT

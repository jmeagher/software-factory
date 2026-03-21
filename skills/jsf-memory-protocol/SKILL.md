# Memory Protocol

Factory agents share state via a JSONL memory file managed by `scripts/memory.py`.

## Memory File Location

`${CLAUDE_PLUGIN_DATA}/memory.jsonl` — persists across sessions and agent invocations.
`CLAUDE_PLUGIN_DATA` is set by Claude Code. In local testing: `export CLAUDE_PLUGIN_DATA=~/.factory`.

## Operations (all via Bash tool)

```bash
# Write a value — returns UUID of the new entry
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write \
  --key "phase_status" --value '{"phase":"planning","status":"complete"}' \
  --tags "phase,orchestration" --agent "${SF_AGENT_ID}"

# Read latest value for a key
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" read --key "phase_status"

# Query by tag (returns JSONL of full entries)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" query --tag "phase"

# List all live keys (call this at agent startup to discover state)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" list-keys

# Delete a specific entry by UUID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" delete --id "<uuid>"

# Garbage collect expired entries (orchestrator calls at session start)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" gc
```

## Well-Known Keys

| Key | Written by | Content |
|-----|-----------|---------|
| `clarification_summary` | clarifier agent | Confirmed Q&A from the user |
| `implementation_plan` | planner agent | Ordered phases with specs |
| `phase_complete:<name>` | implementer agent | Test results, files changed |
| `review_result:<name>` | reviewer agent | Security review outcome |
| `validation_confirmed:<name>` | validator agent | User confirmation timestamp |
| `checkpoint:<name>` | orchestrator | Git commit SHA |
| `main_trace_id` / `main_span_id` | orchestrator | Root OTEL trace context |
| `phase_trace:<name>` / `phase_span:<name>` | orchestrator | Sub-trace context per phase |

## Agent Startup Protocol

Every agent MUST do this before any other action:

1. `list-keys` — discover what state exists
2. `read --key agent_context` — get task assignment and trace ID from orchestrator
3. Export `SF_AGENT_ID` and `SF_TRACE_ID` from the agent context

## Rules

- Never write without exporting `SF_AGENT_ID` — entries without it are hard to trace
- `gc` is only called by the orchestrator at session start — not by subagents
- For time-sensitive state (in-progress locks), use `--ttl 300` (5 minutes) so crashes don't leave stale locks
- Read operations are safe to call without locks; only writes acquire the exclusive lock

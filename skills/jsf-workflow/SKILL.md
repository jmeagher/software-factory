---
name: jsf-workflow
description: Software factory master workflow — use when starting or orchestrating a full factory run, coordinating clarification → spec → TDD implementation → validation phases.
version: 0.1.0
---

# Software Factory Workflow

## Lifecycle

Every factory task follows this sequence. Do not skip or reorder phases.

**Memory operations** are always direct Bash calls — never dispatched as agents. Use `jsf-memory-protocol` skill for the exact commands.

**Agent dispatch** uses the `Agent` tool with these `subagent_type` values:
- Clarifier: `jsf:jsf-clarifier`
- Planner: `jsf:jsf-planner`
- Implementer: `jsf:jsf-implementer`
- Reviewer: `jsf:jsf-reviewer`
- Validator: `jsf:jsf-validator`

1. **Intake** — Accept the request. Run `gc` via Bash (`memory.py gc`). Run `list-keys` via Bash to check for an in-progress task.
2. **Clarification** — Dispatch agent `jsf:jsf-clarifier`. Do not proceed until `clarification_summary` is in memory.
3. **Spec + Plan** — Dispatch agent `jsf:jsf-planner`. Do not proceed until `implementation_plan` is in memory.
4. **Implementation phases** — For each phase in the plan (in order, unless marked parallel):
   a. Commit current state as a checkpoint: `git commit -m "checkpoint: before <phase>"`
   b. Write `phase_start:<name>` to memory via Bash
   c. Dispatch agent `jsf:jsf-implementer` for this phase
   d. When `phase_complete:<name>` appears in memory, dispatch agent `jsf:jsf-reviewer`
   e. When `review_result:<name>` is approved, dispatch agent `jsf:jsf-validator`
   f. When `validation_confirmed:<name>` is in memory, commit: `git commit -m "feat: complete phase <name>"`
5. **Done** — All phases complete. Write `workflow_complete` to memory via Bash with summary.

## Config Layering

At workflow start, check for project-specific overrides in this order:
1. `${PROJECT_ROOT}/.claude/factory-config.json` — structured overrides (see schema below)
2. `${PROJECT_ROOT}/CLAUDE.md` — free-form project guidance

Project-specific rules WIN over factory defaults. Factory defaults are the fallback when neither file exists.

**factory-config.json schema:**
```json
{
  "manual_validation_triggers": ["ui_changes", "api_surface_changes", "external_integrations"],
  "extra_blocked_patterns": ["pattern1", "pattern2"],
  "custom_validation_command": "make test-integration",
  "phase_naming": "kebab-case"
}
```

## Parallelization

Phases marked `parallel: true` in the implementation plan can be dispatched as simultaneous subagents. Use `dispatching-parallel-agents` skill when doing this. Write each agent's context to memory under `agent_context:<agent_id>` before dispatch.

## Context Discipline

Each phase runs in its own subagent. Do not accumulate all phases in the main context. Pass state via memory, not via the conversation. The main orchestrator reads memory checkpoints, not phase-level details.

## Ambiguity Rule

Never assume anything not explicitly stated by the user. If unclear: ask. Do not infer scope, tech stack, or validation requirements.

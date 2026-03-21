# Software Factory Workflow

## Lifecycle

Every factory task follows this sequence. Do not skip or reorder phases.

1. **Intake** — Accept the request. Run `gc` on memory. Read `list-keys` to check for an in-progress task.
2. **Clarification** — Dispatch the clarifier agent. Do not proceed until `clarification_summary` is in memory.
3. **Spec + Plan** — Dispatch the planner agent. Do not proceed until `implementation_plan` is in memory.
4. **Implementation phases** — For each phase in the plan (in order, unless marked parallel):
   a. Commit current state as a checkpoint: `git commit -m "checkpoint: before <phase>"`
   b. Write `phase_start:<name>` to memory
   c. Dispatch the implementer agent for this phase
   d. When `phase_complete:<name>` appears in memory, dispatch the reviewer agent
   e. When `review_result:<name>` is approved, run the validation gate
   f. When `validation_confirmed:<name>` is in memory, commit: `git commit -m "feat: complete phase <name>"`
5. **Done** — All phases complete. Write `workflow_complete` to memory with summary.

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

---
name: jsf-validation-gate
description: Software factory validation gate — use when checking phase completion. Verifies automated tests pass and coordinates manual validation if required.
version: 0.1.0
---

# Validation Gate

## Completion Criteria

A phase is complete when BOTH:
1. Automated tests pass (all tests in the phase's test suite green)
2. Manual validation confirmed, if required

A phase is NOT complete when only one criterion is met.

## Manual Validation Triggers

Manual validation is required for any of:
- UI changes (visual layout, user flows, interactive elements)
- Major API surface changes (new endpoints, changed request/response schemas)
- Changes affecting external integrations (webhooks, third-party APIs, data exports)
- Any change flagged in `manual_validation_triggers` in the project's `factory-config.json`

## Timing

Trigger manual validation requests as early as possible — before implementation of the next phase begins. If the next phase is independent (parallelizable), start it while waiting for manual confirmation.

## Confirmation

Manual validation must be explicitly confirmed by the user. Phrases like "looks good", "LGTM", or "confirmed" count. Silence or ambiguous responses do not count.

Write confirmation to memory:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write \
  --key "validation_confirmed:<phase_name>" \
  --value '{"confirmed_at":"<ISO8601>","by":"user","method":"manual|automated"}' \
  --tags "validation"
```

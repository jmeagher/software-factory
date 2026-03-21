# TDD Implementation

## Red-Green Discipline

For every unit of behavior:
1. Write a failing test that defines the expected behavior
2. Run it — confirm it fails with the right error (not a syntax error)
3. Write minimum code to make it pass
4. Run it — confirm it passes
5. Refactor if needed
6. Repeat for the next behavior

Do not write implementation code before the failing test exists. Do not proceed past a failing test.

## Phase Scope

Read your phase spec from memory (`implementation_plan`, find the matching phase by name). Implement only what is in that phase. If you discover scope that should be in another phase, write a note to memory under `scope_note:<phase_name>` and stop — do not expand scope.

## On Unexpected Failure

If a test fails unexpectedly (not the current TDD step), stop. Write to memory:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write \
  --key "unexpected_failure:<phase_name>" \
  --value '{"test":"<name>","error":"<message>","files_changed":["..."]}' \
  --tags "failure,needs_attention"
```
Then surface the failure to the user. Do not continue with other tests.

## Code Standards (applied before commit)

Every change must be checked by the reviewer agent before committing. The reviewer checks for:
- Hardcoded credentials or secrets (API keys, passwords, tokens in code)
- SQL/shell/XSS injection vectors (unsanitized inputs passed to queries or shell commands)
- Insecure defaults (debug mode left on, auth disabled, `0.0.0.0` binding without intent)
- Missing input validation at system boundaries (user input, external API responses)

Do not commit a phase until the reviewer approves it.

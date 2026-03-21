---
description: Show the current factory workflow state from memory
---

Read factory memory via Bash (`memory.py list-keys`, then `memory.py read --key <key>` for relevant keys). Display:
- Project: `initial_request` summary
- Clarification: confirmed / pending
- Plan: number of phases, phase names
- Each phase: complete / in-progress / not-started, with commit SHA if complete
- Pending validations: any `phase_complete` without `validation_confirmed`
- Memory keys: count of live entries, file location

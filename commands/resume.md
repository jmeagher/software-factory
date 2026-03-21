---
description: Resume a software factory workflow from the last memory checkpoint
---

Read factory memory via Bash (`memory.py list-keys`, then `memory.py read --key <key>` for each relevant key).

Identify the most recent incomplete phase (exists in `implementation_plan` but lacks `validation_confirmed:<name>`).

Display current state to the user:
- Phases completed (with commit SHAs from memory)
- Phase currently in progress (if any)
- Next phase to start

Ask: "Ready to resume from <phase name>?" before proceeding.

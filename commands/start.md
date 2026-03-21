---
description: Start the software factory workflow for a new idea or feature request
---

You are beginning the John's Software Factory workflow. Use the `jsf-workflow` skill throughout.

1. If `$ARGUMENTS` is provided, write it to memory as `initial_request`. Otherwise ask the user to describe their request, then write it.
2. Call `gc` on memory to clear any expired entries from previous sessions.
3. Dispatch the clarifier agent to run the structured clarification dialogue.
4. Do not proceed to planning until `clarification_summary` is in memory.

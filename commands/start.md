---
description: Start the software factory workflow for a new idea or feature request
---

You are beginning the John's Software Factory workflow. Use the `jsf-workflow` skill throughout.

1. If `$ARGUMENTS` is provided, write it to memory as `initial_request` via Bash:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write --key initial_request --value '<the request>'
   ```
   Otherwise ask the user to describe their request, then write it the same way.
2. Run `gc` on memory via Bash to clear any expired entries from previous sessions:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" gc
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" list-keys
   ```
3. Dispatch the clarifier agent (`jsf:jsf-clarifier`) using the Agent tool with `subagent_type: "jsf:jsf-clarifier"`.
4. Do not proceed to planning until `clarification_summary` is in memory.

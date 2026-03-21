#!/usr/bin/env bash
set -euo pipefail

COMMAND=$(cat /dev/stdin | jq -r '.tool_input.command // ""' 2>/dev/null || true)

deny() {
  jq -n --arg r "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

if echo "$COMMAND" | grep -qE 'git[[:space:]]+push' && \
   echo "$COMMAND" | grep -qE '(--force\b|-f\b)' && \
   ! echo "$COMMAND" | grep -q 'force-with-lease'; then
  deny "jsf safety: force push blocked — use --force-with-lease instead"
fi

if echo "$COMMAND" | grep -qE 'git[[:space:]]+reset[[:space:]]+--hard'; then
  deny "jsf safety: git reset --hard blocked — use git stash or a specific safe ref"
fi

if echo "$COMMAND" | grep -qE 'git[[:space:]]+checkout[[:space:]]+--[[:space:]]+\.'; then
  deny "jsf safety: git checkout -- . blocked — discards all working changes"
fi

if echo "$COMMAND" | grep -qE 'git[[:space:]]+clean[[:space:]]+-[a-zA-Z]*f[a-zA-Z]*d'; then
  deny "jsf safety: git clean -fd blocked — deletes untracked files"
fi

exit 0

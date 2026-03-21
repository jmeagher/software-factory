#!/usr/bin/env bash
set -euo pipefail

COMMAND=$(cat /dev/stdin | jq -r '.tool_input.command // ""' 2>/dev/null || true)

if ! echo "$COMMAND" | grep -qiE '(psql|mysql|sqlite3|sqlplus|pgcli)'; then
  exit 0
fi

deny() {
  jq -n --arg r "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
}

UPPER=$(echo "$COMMAND" | tr '[:lower:]' '[:upper:]')

if echo "$UPPER" | grep -qE '(DROP[[:space:]]+(TABLE|DATABASE|SCHEMA)|TRUNCATE[[:space:]])'; then
  deny "jsf safety: destructive SQL DDL blocked (DROP/TRUNCATE)"
fi

if echo "$UPPER" | grep -qE "(^|[[:space:]']|-)DELETE[[:space:]]+FROM[[:space:]]" && \
   ! echo "$UPPER" | grep -qE '[[:space:]]WHERE[[:space:]]'; then
  deny "jsf safety: DELETE without WHERE clause blocked"
fi

if echo "$UPPER" | grep -qE "(^|[[:space:]']|-)UPDATE[[:space:]]+[A-Z_]+[[:space:]]+SET[[:space:]]" && \
   ! echo "$UPPER" | grep -qE '[[:space:]]WHERE[[:space:]]'; then
  deny "jsf safety: UPDATE without WHERE clause blocked"
fi

exit 0

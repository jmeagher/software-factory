#!/usr/bin/env bash
set -euo pipefail

COMMAND=$(cat /dev/stdin | jq -r '.tool_input.command // ""' 2>/dev/null || true)

BLOCKED_PATTERNS=(
  'rm[[:space:]]+-[a-zA-Z]*r[a-zA-Z]*f'
  'rm[[:space:]]+-[a-zA-Z]*f[a-zA-Z]*r'
  'find[[:space:]].*-delete'
  'find[[:space:]].*-exec[[:space:]]rm'
  'dd[[:space:]].*of=/dev/[a-z]'
  'mkfs\.'
  ':\(\)\{.*\|.*:.*\}.*:'
)

for PATTERN in "${BLOCKED_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qE "$PATTERN"; then
    jq -n '{
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: "jsf safety: destructive shell command blocked"
      }
    }'
    exit 0
  fi
done

exit 0

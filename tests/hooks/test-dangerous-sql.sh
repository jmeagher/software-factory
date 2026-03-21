#!/usr/bin/env bash
set -euo pipefail
# Run from repo root: bash tests/hooks/test-dangerous-sql.sh
HOOK="hooks/scripts/block-dangerous-sql.sh"
PASS=0; FAIL=0

check_blocked() {
  local label="$1" cmd="$2"
  local input; input=$(jq -n --arg c "$cmd" '{tool_input:{command:$c}}')
  local out; out=$(echo "$input" | bash "$HOOK")
  local decision; decision=$(echo "$out" | jq -r '.hookSpecificOutput.permissionDecision // "allow"')
  if [[ "$decision" == "deny" ]]; then echo "PASS: blocked [$label]"; ((PASS++)) || true
  else echo "FAIL: should block [$label]"; ((FAIL++)) || true; fi
}

check_allowed() {
  local label="$1" cmd="$2"
  local input; input=$(jq -n --arg c "$cmd" '{tool_input:{command:$c}}')
  local out; out=$(echo "$input" | bash "$HOOK")
  local decision; decision=$(echo "$out" | jq -r '.hookSpecificOutput.permissionDecision // "allow"')
  if [[ "$decision" != "deny" ]]; then echo "PASS: allowed [$label]"; ((PASS++)) || true
  else echo "FAIL: should allow [$label]"; ((FAIL++)) || true; fi
}

check_blocked "DROP TABLE"           "psql -c 'DROP TABLE users'"
check_blocked "DROP DATABASE"        "psql -c 'DROP DATABASE prod'"
check_blocked "TRUNCATE"             "psql -c 'TRUNCATE TABLE events'"
check_blocked "DELETE without WHERE" "psql -c 'DELETE FROM logs'"
check_blocked "UPDATE without WHERE" "mysql -e 'UPDATE users SET active=0'"

check_allowed "non-db command"       "echo 'DROP TABLE foo'"
check_allowed "DELETE with WHERE"    "psql -c 'DELETE FROM logs WHERE created_at < now()'"
check_allowed "UPDATE with WHERE"    "psql -c 'UPDATE users SET name=\$1 WHERE id=\$2'"
check_allowed "SELECT"               "psql -c 'SELECT count(*) FROM users'"

echo ""; echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]

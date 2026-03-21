#!/usr/bin/env bash
set -euo pipefail
# Run from repo root: bash tests/hooks/test-dangerous-git.sh
HOOK="hooks/scripts/block-dangerous-git.sh"
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

check_blocked "force push --force"         "git push origin main --force"
check_blocked "force push -f"             "git push -f origin main"
check_blocked "reset --hard"              "git reset --hard HEAD~3"
check_blocked "checkout -- ."             "git checkout -- ."
check_blocked "clean -fd"                 "git clean -fd"
check_blocked "force push -f flag first"  "git push -f origin main"
check_blocked "force to backup branch"    "git push --force origin backup-branch"
check_blocked "force to upstream remote"  "git push upstream main --force"

check_allowed "force-with-lease"          "git push --force-with-lease origin main"
check_allowed "force-with-lease no args"  "git push --force-with-lease"
check_allowed "normal push"               "git push origin main"
check_allowed "reset HEAD (stage)"        "git reset HEAD myfile.txt"
check_allowed "normal checkout"           "git checkout my-branch"

echo ""; echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]

#!/usr/bin/env bash
set -euo pipefail
# Run from repo root: bash tests/hooks/test-dangerous-bash.sh
HOOK="hooks/scripts/block-dangerous-bash.sh"
PASS=0; FAIL=0

check_blocked() {
  local label="$1" cmd="$2"
  local input; input=$(jq -n --arg c "$cmd" '{tool_input:{command:$c}}')
  local out; out=$(echo "$input" | bash "$HOOK")
  local decision; decision=$(echo "$out" | jq -r '.hookSpecificOutput.permissionDecision // "allow"')
  if [[ "$decision" == "deny" ]]; then
    echo "PASS: blocked [$label]"; ((PASS++)) || true
  else
    echo "FAIL: should block [$label] but got [$decision]"; ((FAIL++)) || true
  fi
}

check_allowed() {
  local label="$1" cmd="$2"
  local input; input=$(jq -n --arg c "$cmd" '{tool_input:{command:$c}}')
  local out; out=$(echo "$input" | bash "$HOOK")
  local decision; decision=$(echo "$out" | jq -r '.hookSpecificOutput.permissionDecision // "allow"')
  if [[ "$decision" != "deny" ]]; then
    echo "PASS: allowed [$label]"; ((PASS++)) || true
  else
    echo "FAIL: should allow [$label] but blocked"; ((FAIL++)) || true
  fi
}

# Must be blocked
check_blocked "rm -rf"             "rm -rf /tmp/foo"
check_blocked "rm -fr"             "rm -fr /tmp/foo"
check_blocked "rm -rrf"            "rm -rrf /tmp/foo"
check_blocked "find -delete"       "find . -name '*.tmp' -delete"
check_blocked "find exec rm"       "find . -exec rm -rf {} +"
check_blocked "dd to block device" "dd if=/dev/zero of=/dev/sda"
check_blocked "mkfs"               "mkfs.ext4 /dev/sdb1"
check_blocked "fork bomb"          ":(){ :|:& };:"
check_blocked "rm -rf quoted var"  'rm -rf "$HOME/tmp"'
check_blocked "rm -rf eval"        'eval "rm -rf /"'

# Must be allowed
check_allowed "rm single file"     "rm /tmp/foo.txt"
check_allowed "rm -f single file"  "rm -f /tmp/foo.txt"
check_allowed "normal find"        "find . -name '*.py'"
check_allowed "dd file to file"    "dd if=input.bin of=output.bin"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]

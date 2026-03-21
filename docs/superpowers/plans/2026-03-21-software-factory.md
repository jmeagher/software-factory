# Software Factory Plugin — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a software factory delivered as a Claude Code plugin (with Cursor as a later step) that takes any project from initial idea to fully implemented system via interactive, phased, AI-assisted workflow.

**Architecture:** Plugin-based system using Claude Code's skills/commands/hooks/agents primitives. Safety is enforced via PreToolUse hooks; workflow state is persisted in JSONL memory with file locking; observability is provided via OpenTelemetry. Each subsystem is independently deployable.

**Tech Stack:** Bash (hooks), Python 3.x (memory + OTEL), Markdown (skills/commands/agents), JSON (plugin manifest + hooks config), JSONL (memory store), opentelemetry-sdk + opentelemetry-exporter-otlp-proto-grpc (telemetry)

**Sub-Plans (build order — each produces independently testable output):**
1. [Plugin Scaffold](#sub-plan-1-plugin-scaffold) — directory structure, manifest, loads in Claude Code
2. [Safety Hooks](#sub-plan-2-safety-hooks) — ✅ **First testable increment** — blocks dangerous commands
3. [Memory System](#sub-plan-3-memory-system) — Python JSONL memory with file locking *(build before workflow — workflow agents write to memory)*
4. [Core Workflow](#sub-plan-4-core-workflow) — skills, commands, agents for the full factory flow *(requires memory from sub-plan 3)*
5. [OpenTelemetry Monitoring](#sub-plan-5-opentelemetry-monitoring) — traces for all factory work with bi-directional links
6. [Cursor Support](#sub-plan-6-cursor-support) — .cursor-plugin/ + .mdc rules for Cursor IDE compatibility

---

## Context

This factory is a meta-tool: it helps developers build other software by orchestrating a structured AI-assisted workflow. It is delivered as a plugin so it can be installed once and applied to any project. The factory must be safe (hook-enforced guardrails), reliable (TDD + validation gates), efficient (subagent-per-task, lean context), and observable (OTEL traces). Project-specific rules (in `.claude/factory-config.json` or `CLAUDE.md`) override factory defaults.

---

## Project File Structure

```
software-factory/
├── .claude-plugin/
│   └── plugin.json                         # Claude Code plugin manifest
├── hooks/
│   ├── hooks.json                           # Hook registrations
│   └── scripts/
│       ├── block-dangerous-bash.sh          # PreToolUse: rm -rf, dd, fork bombs
│       ├── block-dangerous-git.sh           # PreToolUse: force-push, reset --hard
│       └── block-dangerous-sql.sh           # PreToolUse: DROP/TRUNCATE/DELETE without WHERE
├── scripts/
│   ├── memory.py                            # JSONL memory subsystem
│   ├── telemetry.py                         # OpenTelemetry span management
│   └── requirements.txt                     # Python deps (opentelemetry-*)
├── skills/
│   ├── jsf-workflow/SKILL.md            # Master orchestration guidance
│   ├── jsf-clarification/SKILL.md              # Structured clarification dialogue
│   ├── jsf-spec-planning/SKILL.md              # Tech spec + phased implementation plan
│   ├── jsf-tdd-implementation/SKILL.md         # Red-green TDD discipline
│   ├── jsf-validation-gate/SKILL.md            # Phase completion criteria
│   ├── jsf-memory-protocol/SKILL.md            # How agents read/write memory
│   └── jsf-otel-tracing/SKILL.md              # How agents emit spans
├── commands/
│   ├── jsf-start.md                             # /jsf:start
│   ├── jsf-resume.md                            # /jsf:resume
│   ├── jsf-validate.md                          # /jsf:validate
│   └── jsf-status.md                            # /jsf:status
├── agents/
│   ├── jsf-clarifier.md
│   ├── jsf-planner.md
│   ├── jsf-implementer.md
│   ├── jsf-reviewer.md
│   └── jsf-validator.md
├── tests/
│   ├── hooks/
│   │   ├── test-dangerous-bash.sh
│   │   ├── test-dangerous-git.sh
│   │   └── test-dangerous-sql.sh
│   ├── memory/
│   │   └── test_memory.py
│   └── telemetry/
│       └── test_telemetry.py
├── .cursor-plugin/
│   └── plugin.json                          # Cursor manifest
└── rules/                                   # Cursor .mdc rule files
    ├── jsf-workflow.mdc
    ├── jsf-clarification.mdc
    ├── jsf-spec-planning.mdc
    ├── jsf-tdd-implementation.mdc
    ├── jsf-validation-gate.mdc
    ├── jsf-memory-protocol.mdc
    └── jsf-otel-tracing.mdc
```

---

## Sub-Plan 1: Plugin Scaffold

**Goal:** Create the minimal plugin structure that Claude Code recognizes and loads. Establishes `CLAUDE_PLUGIN_ROOT`.

**Note on `CLAUDE_PLUGIN_ROOT`:** Claude Code sets this environment variable to the plugin's installation directory when invoking hooks. In `hooks/hooks.json`, references to `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/...` resolve correctly at runtime because Claude Code expands this variable before executing hook commands. No manual setup is needed. To test locally (outside Claude Code), export it manually: `export CLAUDE_PLUGIN_ROOT=$(pwd)`.

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `hooks/hooks.json` (empty)

### Task 1.1: Plugin manifest

- [x] **Step 1: Create `.claude-plugin/plugin.json`**

```json
{
  "name": "jsf",
  "version": "0.1.0",
  "description": "John's Software Factory — takes projects from idea to implementation via phased, validated workflow.",
  "author": { "name": "jmeagher" },
  "license": "MIT"
}
```

- [x] **Step 1.5: Create `.claude-plugin/marketplace.json`**

```json
{
  "name": "jsf",
  "owner": { "name": "jmeagher" },
  "metadata": {
    "description": "John's Software Factory — takes projects from idea to implementation via phased, validated workflow."
  },
  "plugins": [
    {
      "name": "jsf",
      "source": "./",
      "description": "Software factory plugin: clarification, planning, TDD implementation, validation gates, and memory coordination.",
      "license": "MIT"
    }
  ]
}
```

Add marketplace with: `/plugin marketplace add jmeagher/software-factory` (GitHub) or `/plugin marketplace add /path/to/software-factory` (local).

- [x] **Step 2: Create `hooks/hooks.json` (empty, ready for population)**

```json
{
  "hooks": {}
}
```

- [ ] **Step 3: Verify Claude Code loads the plugin**

```bash
export CLAUDE_PLUGIN_ROOT=$(pwd)
claude --plugin-dir . --print "List loaded plugins"
```
Expected: plugin `jsf` appears in loaded plugins list.

- [x] **Step 4: Commit**

```bash
git add -f .claude-plugin/plugin.json .claude-plugin/marketplace.json hooks/hooks.json
git commit -m "feat: add plugin manifest, marketplace config, and empty hooks config"
```

Note: `-f` required because global gitignore matches `.*` — force-add is intentional for plugin files.

---

## Sub-Plan 2: Safety Hooks

**Goal:** Block dangerous shell commands, git operations, and SQL before they execute. This is the first independently testable increment — no workflow required.

**Files:**
- Modify: `hooks/hooks.json`
- Create: `hooks/scripts/block-dangerous-bash.sh`
- Create: `hooks/scripts/block-dangerous-git.sh`
- Create: `hooks/scripts/block-dangerous-sql.sh`
- Create: `tests/hooks/test-dangerous-bash.sh`
- Create: `tests/hooks/test-dangerous-git.sh`
- Create: `tests/hooks/test-dangerous-sql.sh`

### Task 2.1: Dangerous bash hook

- [ ] **Step 1: Write failing test for bash hook**

Create `tests/hooks/test-dangerous-bash.sh`:
```bash
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
    echo "PASS: blocked [$label]"; ((PASS++))
  else
    echo "FAIL: should block [$label] but got [$decision]"; ((FAIL++))
  fi
}

check_allowed() {
  local label="$1" cmd="$2"
  local input; input=$(jq -n --arg c "$cmd" '{tool_input:{command:$c}}')
  local out; out=$(echo "$input" | bash "$HOOK")
  local decision; decision=$(echo "$out" | jq -r '.hookSpecificOutput.permissionDecision // "allow"')
  if [[ "$decision" != "deny" ]]; then
    echo "PASS: allowed [$label]"; ((PASS++))
  else
    echo "FAIL: should allow [$label] but blocked"; ((FAIL++))
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

# Must be allowed
check_allowed "rm single file"     "rm /tmp/foo.txt"
check_allowed "rm -f single file"  "rm -f /tmp/foo.txt"
check_allowed "normal find"        "find . -name '*.py'"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 2: Run test — verify it fails (hook script doesn't exist yet)**

```bash
# From repo root
bash tests/hooks/test-dangerous-bash.sh
```
Expected: error — `hooks/scripts/block-dangerous-bash.sh: No such file or directory`

- [ ] **Step 3: Create `hooks/scripts/block-dangerous-bash.sh`**

```bash
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
```

```bash
chmod +x hooks/scripts/block-dangerous-bash.sh
```

- [ ] **Step 4: Run test — verify it passes**

```bash
bash tests/hooks/test-dangerous-bash.sh
```
Expected: all PASS, exit 0

- [ ] **Step 5: Commit**

```bash
git add hooks/scripts/block-dangerous-bash.sh tests/hooks/test-dangerous-bash.sh
git commit -m "feat: add dangerous bash command safety hook with tests"
```

### Task 2.2: Dangerous git hook

- [ ] **Step 1: Write failing test**

Create `tests/hooks/test-dangerous-git.sh`:
```bash
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
  if [[ "$decision" == "deny" ]]; then echo "PASS: blocked [$label]"; ((PASS++))
  else echo "FAIL: should block [$label]"; ((FAIL++)); fi
}

check_allowed() {
  local label="$1" cmd="$2"
  local input; input=$(jq -n --arg c "$cmd" '{tool_input:{command:$c}}')
  local out; out=$(echo "$input" | bash "$HOOK")
  local decision; decision=$(echo "$out" | jq -r '.hookSpecificOutput.permissionDecision // "allow"')
  if [[ "$decision" != "deny" ]]; then echo "PASS: allowed [$label]"; ((PASS++))
  else echo "FAIL: should allow [$label]"; ((FAIL++)); fi
}

check_blocked "force push --force"  "git push origin main --force"
check_blocked "force push -f"       "git push -f origin main"
check_blocked "reset --hard"        "git reset --hard HEAD~3"
check_blocked "checkout -- ."       "git checkout -- ."
check_blocked "clean -fd"           "git clean -fd"

check_allowed "force-with-lease"    "git push --force-with-lease origin main"
check_allowed "normal push"         "git push origin main"
check_allowed "reset HEAD (stage)"  "git reset HEAD myfile.txt"
check_allowed "normal checkout"     "git checkout my-branch"

echo ""; echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
```

- [ ] **Step 2: Run test — verify it fails**

```bash
bash tests/hooks/test-dangerous-git.sh
```

- [ ] **Step 3: Create `hooks/scripts/block-dangerous-git.sh`**

```bash
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
```

```bash
chmod +x hooks/scripts/block-dangerous-git.sh
```

- [ ] **Step 4: Run test — verify it passes**

```bash
bash tests/hooks/test-dangerous-git.sh
```

- [ ] **Step 5: Commit**

```bash
git add hooks/scripts/block-dangerous-git.sh tests/hooks/test-dangerous-git.sh
git commit -m "feat: add dangerous git command safety hook with tests"
```

### Task 2.3: Dangerous SQL hook

- [ ] **Step 1: Write failing test**

Create `tests/hooks/test-dangerous-sql.sh`:
```bash
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
  if [[ "$decision" == "deny" ]]; then echo "PASS: blocked [$label]"; ((PASS++))
  else echo "FAIL: should block [$label]"; ((FAIL++)); fi
}

check_allowed() {
  local label="$1" cmd="$2"
  local input; input=$(jq -n --arg c "$cmd" '{tool_input:{command:$c}}')
  local out; out=$(echo "$input" | bash "$HOOK")
  local decision; decision=$(echo "$out" | jq -r '.hookSpecificOutput.permissionDecision // "allow"')
  if [[ "$decision" != "deny" ]]; then echo "PASS: allowed [$label]"; ((PASS++))
  else echo "FAIL: should allow [$label]"; ((FAIL++)); fi
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
```

- [ ] **Step 2: Run test — verify it fails**

```bash
bash tests/hooks/test-dangerous-sql.sh
```

- [ ] **Step 3: Create `hooks/scripts/block-dangerous-sql.sh`**

```bash
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

if echo "$UPPER" | grep -qE '[[:space:]]DELETE[[:space:]]+FROM[[:space:]]' && \
   ! echo "$UPPER" | grep -qE '[[:space:]]WHERE[[:space:]]'; then
  deny "jsf safety: DELETE without WHERE clause blocked"
fi

if echo "$UPPER" | grep -qE '[[:space:]]UPDATE[[:space:]]+[A-Z_]+[[:space:]]+SET[[:space:]]' && \
   ! echo "$UPPER" | grep -qE '[[:space:]]WHERE[[:space:]]'; then
  deny "jsf safety: UPDATE without WHERE clause blocked"
fi

exit 0
```

```bash
chmod +x hooks/scripts/block-dangerous-sql.sh
```

- [ ] **Step 4: Run test — verify it passes**

```bash
bash tests/hooks/test-dangerous-sql.sh
```

- [ ] **Step 5: Commit**

```bash
git add hooks/scripts/block-dangerous-sql.sh tests/hooks/test-dangerous-sql.sh
git commit -m "feat: add dangerous SQL safety hook with tests"
```

### Task 2.4: Wire hooks into plugin

- [ ] **Step 1: Update `hooks/hooks.json`**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/block-dangerous-bash.sh",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/block-dangerous-git.sh",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/scripts/block-dangerous-sql.sh",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Verify hooks fire in Claude Code**

```bash
# Load the plugin (CLAUDE_PLUGIN_ROOT is set automatically by Claude Code)
claude --plugin-dir .
# In the Claude session, ask it to run:
#   Run the command: rm -rf /tmp/test
# Expected output contains: "jsf safety: destructive shell command blocked"
```

- [ ] **Step 3: Run all hook tests from repo root**

```bash
bash tests/hooks/test-dangerous-bash.sh && \
bash tests/hooks/test-dangerous-git.sh && \
bash tests/hooks/test-dangerous-sql.sh
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add hooks/hooks.json
git commit -m "feat: wire all three safety hooks into plugin PreToolUse"
```

---

## Sub-Plan 3: Memory System

**Goal:** Python JSONL memory store with file-based exclusive locking for multi-agent coordination across sessions. **Build this before the core workflow** — workflow agents write to memory at runtime.

**Files:**
- Create: `scripts/memory.py`
- Create: `skills/jsf-memory-protocol/SKILL.md`
- Create: `tests/memory/test_memory.py`

### Task 3.1: Memory script with tests

- [ ] **Step 1: Write failing tests**

Create `tests/memory/test_memory.py`:
```python
import subprocess, json, os, tempfile, time, pytest
from pathlib import Path
import concurrent.futures

# Run from repo root: python3 -m pytest tests/memory/test_memory.py -v
SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "memory.py"

@pytest.fixture
def mem_env(tmp_path):
    return {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path), "SF_AGENT_ID": "test"}

def run(args, env):
    return subprocess.run(
        ["python3", str(SCRIPT)] + args,
        capture_output=True, text=True, env=env
    )

def test_write_and_read(mem_env):
    run(["write", "--key", "foo", "--value", '"bar"'], mem_env)
    r = run(["read", "--key", "foo"], mem_env)
    assert r.returncode == 0
    assert json.loads(r.stdout) == "bar"

def test_latest_wins(mem_env):
    run(["write", "--key", "x", "--value", '"first"'], mem_env)
    run(["write", "--key", "x", "--value", '"second"'], mem_env)
    r = run(["read", "--key", "x"], mem_env)
    assert json.loads(r.stdout) == "second"

def test_missing_key_returns_null(mem_env):
    r = run(["read", "--key", "nonexistent"], mem_env)
    assert r.returncode == 0
    assert r.stdout.strip() == "null"

def test_list_keys(mem_env):
    run(["write", "--key", "a", "--value", "1"], mem_env)
    run(["write", "--key", "b", "--value", "2"], mem_env)
    r = run(["list-keys"], mem_env)
    keys = json.loads(r.stdout)
    assert "a" in keys and "b" in keys

def test_query_by_tag(mem_env):
    run(["write", "--key", "p1", "--value", '"v1"', "--tags", "phase,planning"], mem_env)
    run(["write", "--key", "p2", "--value", '"v2"', "--tags", "phase,impl"], mem_env)
    run(["write", "--key", "other", "--value", '"v3"', "--tags", "misc"], mem_env)
    r = run(["query", "--tag", "phase"], mem_env)
    lines = [l for l in r.stdout.strip().split("\n") if l]
    assert len(lines) == 2

def test_delete(mem_env):
    entry_id = run(["write", "--key", "del_me", "--value", '"x"'], mem_env).stdout.strip()
    run(["delete", "--id", entry_id], mem_env)
    r = run(["read", "--key", "del_me"], mem_env)
    assert r.stdout.strip() == "null"

def test_gc_removes_expired(mem_env):
    run(["write", "--key", "short", "--value", '"bye"', "--ttl", "1"], mem_env)
    time.sleep(2)
    run(["gc"], mem_env)
    r = run(["read", "--key", "short"], mem_env)
    assert r.stdout.strip() == "null"

def test_parallel_write_no_corruption(mem_env):
    """Two processes write concurrently; file must contain valid JSONL."""
    def write_n(n):
        for i in range(10):
            run(["write", "--key", f"k{n}_{i}", "--value", str(i)], mem_env)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(write_n, [0, 1]))
    data_file = Path(mem_env["CLAUDE_PLUGIN_DATA"]) / "memory.jsonl"
    for line in data_file.read_text().strip().split("\n"):
        if line:
            json.loads(line)  # must not raise
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python3 -m pytest tests/memory/test_memory.py -v
```
Expected: `FileNotFoundError` or `ModuleNotFoundError` since `scripts/memory.py` doesn't exist.

- [ ] **Step 3: Create `scripts/memory.py`**

```python
#!/usr/bin/env python3
"""
JSONL memory store for jsf multi-agent coordination.

Usage:
  memory.py write  --key KEY --value JSON [--tags t1,t2] [--ttl SECONDS] [--agent ID]
  memory.py read   --key KEY
  memory.py query  [--key KEY] [--tag TAG] [--agent ID]
  memory.py delete --id UUID
  memory.py gc
  memory.py list-keys
"""
import argparse, fcntl, json, os, sys, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path


def _memory_file() -> Path:
    data_dir = os.environ.get("CLAUDE_PLUGIN_DATA", str(Path.home() / ".factory"))
    p = Path(data_dir) / "memory.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch(exist_ok=True)
    return p


def _read_all(fh) -> list:
    fh.seek(0)
    result = []
    for line in fh:
        line = line.strip()
        if line:
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return result


def _is_live(entry: dict) -> bool:
    exp = entry.get("expires_at")
    if not exp:
        return True
    return datetime.fromisoformat(exp) > datetime.now(timezone.utc)


def cmd_write(args):
    now = datetime.now(timezone.utc)
    entry = {
        "id": str(uuid.uuid4()),
        "key": args.key,
        "value": json.loads(args.value),
        "tags": [t.strip() for t in args.tags.split(",")] if args.tags else [],
        "agent_id": args.agent or os.environ.get("SF_AGENT_ID", "unknown"),
        "trace_id": os.environ.get("SF_TRACE_ID", ""),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=int(args.ttl))).isoformat() if args.ttl else None,
        "session_id": os.environ.get("CLAUDE_SESSION_ID", ""),
    }
    path = _memory_file()
    with open(path, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            fh.write(json.dumps(entry) + "\n")
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    print(entry["id"])


def cmd_read(args):
    path = _memory_file()
    with open(path, "r") as fh:
        fcntl.flock(fh, fcntl.LOCK_SH)
        try:
            entries = _read_all(fh)
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    matches = [e for e in entries if e["key"] == args.key and _is_live(e)]
    print(json.dumps(matches[-1]["value"]) if matches else "null")


def cmd_query(args):
    path = _memory_file()
    with open(path, "r") as fh:
        fcntl.flock(fh, fcntl.LOCK_SH)
        try:
            entries = _read_all(fh)
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    results = [e for e in entries if _is_live(e)]
    if args.key:
        results = [e for e in results if e["key"] == args.key]
    if args.tag:
        results = [e for e in results if args.tag in e.get("tags", [])]
    if args.agent:
        results = [e for e in results if e.get("agent_id") == args.agent]
    for e in results:
        print(json.dumps(e))


def cmd_delete(args):
    path = _memory_file()
    with open(path, "r+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            entries = _read_all(fh)
            remaining = [e for e in entries if e["id"] != args.id]
            fh.seek(0); fh.truncate()
            for e in remaining:
                fh.write(json.dumps(e) + "\n")
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def cmd_gc(args):
    path = _memory_file()
    with open(path, "r+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            entries = _read_all(fh)
            live = [e for e in entries if _is_live(e)]
            removed = len(entries) - len(live)
            fh.seek(0); fh.truncate()
            for e in live:
                fh.write(json.dumps(e) + "\n")
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    print(f"gc: removed {removed} expired entries, {len(live)} remaining")


def cmd_list_keys(args):
    path = _memory_file()
    with open(path, "r") as fh:
        fcntl.flock(fh, fcntl.LOCK_SH)
        try:
            entries = _read_all(fh)
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    live = [e for e in entries if _is_live(e)]
    by_key: dict = {}
    for e in live:
        k = e["key"]
        if k not in by_key:
            by_key[k] = {"count": 0, "latest_ts": "", "latest_id": ""}
        by_key[k]["count"] += 1
        if e["created_at"] >= by_key[k]["latest_ts"]:
            by_key[k]["latest_ts"] = e["created_at"]
            by_key[k]["latest_id"] = e["id"]
    print(json.dumps(by_key))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")

    w = sub.add_parser("write")
    w.add_argument("--key", required=True)
    w.add_argument("--value", required=True)
    w.add_argument("--tags"); w.add_argument("--ttl"); w.add_argument("--agent")

    r = sub.add_parser("read"); r.add_argument("--key", required=True)

    q = sub.add_parser("query")
    q.add_argument("--key"); q.add_argument("--tag"); q.add_argument("--agent")

    d = sub.add_parser("delete"); d.add_argument("--id", required=True)
    sub.add_parser("gc")
    sub.add_parser("list-keys")

    args = p.parse_args()
    dispatch = {"write": cmd_write, "read": cmd_read, "query": cmd_query,
                "delete": cmd_delete, "gc": cmd_gc, "list-keys": cmd_list_keys}
    if args.cmd in dispatch:
        dispatch[args.cmd](args)
    else:
        p.print_help(); sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python3 -m pytest tests/memory/test_memory.py -v
```
Expected: all 8 tests pass.

- [ ] **Step 5: Create `skills/jsf-memory-protocol/SKILL.md`**

```markdown
# Memory Protocol

Factory agents share state via a JSONL memory file managed by `scripts/memory.py`.

## Memory File Location

`${CLAUDE_PLUGIN_DATA}/memory.jsonl` — persists across sessions and agent invocations.
`CLAUDE_PLUGIN_DATA` is set by Claude Code. In local testing: `export CLAUDE_PLUGIN_DATA=~/.factory`.

## Operations (all via Bash tool)

```bash
# Write a value — returns UUID of the new entry
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write \
  --key "phase_status" --value '{"phase":"planning","status":"complete"}' \
  --tags "phase,orchestration" --agent "${SF_AGENT_ID}"

# Read latest value for a key
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" read --key "phase_status"

# Query by tag (returns JSONL of full entries)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" query --tag "phase"

# List all live keys (call this at agent startup to discover state)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" list-keys

# Delete a specific entry by UUID
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" delete --id "<uuid>"

# Garbage collect expired entries (orchestrator calls at session start)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" gc
```

## Well-Known Keys

| Key | Written by | Content |
|-----|-----------|---------|
| `clarification_summary` | clarifier agent | Confirmed Q&A from the user |
| `implementation_plan` | planner agent | Ordered phases with specs |
| `phase_complete:<name>` | implementer agent | Test results, files changed |
| `review_result:<name>` | reviewer agent | Security review outcome |
| `validation_confirmed:<name>` | validator agent | User confirmation timestamp |
| `checkpoint:<name>` | orchestrator | Git commit SHA |
| `main_trace_id` / `main_span_id` | orchestrator | Root OTEL trace context |
| `phase_trace:<name>` / `phase_span:<name>` | orchestrator | Sub-trace context per phase |

## Agent Startup Protocol

Every agent MUST do this before any other action:

1. `list-keys` — discover what state exists
2. `read --key agent_context` — get task assignment and trace ID from orchestrator
3. Export `SF_AGENT_ID` and `SF_TRACE_ID` from the agent context

## Rules

- Never write without exporting `SF_AGENT_ID` — entries without it are hard to trace
- `gc` is only called by the orchestrator at session start — not by subagents
- For time-sensitive state (in-progress locks), use `--ttl 300` (5 minutes) so crashes don't leave stale locks
- Read operations are safe to call without locks; only writes acquire the exclusive lock
```

- [ ] **Step 6: Commit**

```bash
git add scripts/memory.py skills/jsf-memory-protocol/SKILL.md tests/memory/
git commit -m "feat: add JSONL memory system with file locking, tests, and skill"
```

---

## Sub-Plan 4: Core Workflow

**Goal:** Skills, commands, and agents implementing the full factory workflow. **Requires Sub-Plan 3 (memory) to be complete** — agents write to memory at runtime.

**Files:**
- Create: `skills/jsf-workflow/SKILL.md`
- Create: `skills/jsf-clarification/SKILL.md`
- Create: `skills/jsf-spec-planning/SKILL.md`
- Create: `skills/jsf-tdd-implementation/SKILL.md`
- Create: `skills/jsf-validation-gate/SKILL.md`
- Create: `commands/jsf-start.md`, `commands/jsf-resume.md`, `commands/jsf-validate.md`, `commands/jsf-status.md`
- Create: `agents/jsf-clarifier.md`, `agents/jsf-planner.md`, `agents/jsf-implementer.md`, `agents/jsf-reviewer.md`, `agents/jsf-validator.md`

### Task 4.1: Factory workflow skill (master orchestration)

- [ ] **Step 1: Verify plugin loads before writing skill**

```bash
export CLAUDE_PLUGIN_ROOT=$(pwd)
claude --plugin-dir . --print "What plugin skills are loaded?" 2>&1 | grep -i "factory\|No skills"
```
Expected: "No skills" or plugin listed (baseline before adding skills).

- [ ] **Step 2: Create `skills/jsf-workflow/SKILL.md`**

```markdown
# Software Factory Workflow

## Lifecycle

Every factory task follows this sequence. Do not skip or reorder phases.

1. **Intake** — Accept the request. Run `gc` on memory. Read `list-keys` to check for an in-progress task.
2. **Clarification** — Dispatch the clarifier agent. Do not proceed until `clarification_summary` is in memory.
3. **Spec + Plan** — Dispatch the planner agent. Do not proceed until `implementation_plan` is in memory.
4. **Implementation phases** — For each phase in the plan (in order, unless marked parallel):
   a. Commit current state as a checkpoint: `git commit -m "checkpoint: before <phase>"`
   b. Write `phase_start:<name>` to memory
   c. Dispatch the implementer agent for this phase
   d. When `phase_complete:<name>` appears in memory, dispatch the reviewer agent
   e. When `review_result:<name>` is approved, run the validation gate
   f. When `validation_confirmed:<name>` is in memory, commit: `git commit -m "feat: complete phase <name>"`
5. **Done** — All phases complete. Write `workflow_complete` to memory with summary.

## Config Layering

At workflow start, check for project-specific overrides in this order:
1. `${PROJECT_ROOT}/.claude/factory-config.json` — structured overrides (see schema below)
2. `${PROJECT_ROOT}/CLAUDE.md` — free-form project guidance

Project-specific rules WIN over factory defaults. Factory defaults are the fallback when neither file exists.

**factory-config.json schema:**
```json
{
  "manual_validation_triggers": ["ui_changes", "api_surface_changes", "external_integrations"],
  "extra_blocked_patterns": ["pattern1", "pattern2"],
  "custom_validation_command": "make test-integration",
  "phase_naming": "kebab-case"
}
```

## Parallelization

Phases marked `parallel: true` in the implementation plan can be dispatched as simultaneous subagents. Use `dispatching-parallel-agents` skill when doing this. Write each agent's context to memory under `agent_context:<agent_id>` before dispatch.

## Context Discipline

Each phase runs in its own subagent. Do not accumulate all phases in the main context. Pass state via memory, not via the conversation. The main orchestrator reads memory checkpoints, not phase-level details.

## Ambiguity Rule

Never assume anything not explicitly stated by the user. If unclear: ask. Do not infer scope, tech stack, or validation requirements.
```

- [ ] **Step 3: Verify skill loads**

```bash
claude --plugin-dir . --print "What skills do you have from the jsf plugin?"
```
Expected: mentions `jsf-workflow` skill.

- [ ] **Step 4: Test config layering**

```bash
# Create a test project directory with a factory-config.json
mkdir -p /tmp/sf-test-project/.claude
cat > /tmp/sf-test-project/.claude/factory-config.json <<'EOF'
{"manual_validation_triggers": ["ui_changes"], "phase_naming": "snake_case"}
EOF

# Ask Claude to describe the factory config it would use for /tmp/sf-test-project
PROJECT_ROOT=/tmp/sf-test-project claude --plugin-dir . \
  --print "Using the jsf-workflow skill, what manual_validation_triggers would apply to the project at /tmp/sf-test-project?"
```
Expected: Claude reads and reports `["ui_changes"]` from the project config, not the factory default list.

- [ ] **Step 5: Commit**

```bash
git add skills/jsf-workflow/SKILL.md
git commit -m "feat: add factory-workflow master orchestration skill"
```

### Task 4.2: Clarification skill and agent

- [ ] **Step 1: Create `skills/jsf-clarification/SKILL.md`**

```markdown
# Clarification

## Purpose

Gather everything needed before any planning begins. One organized batch of questions — not a back-and-forth interrogation.

## Question Categories (cover all that apply)

1. **Scope**: What is in scope? What is explicitly out of scope?
2. **Success criteria**: What does done look like? How will we know it works?
3. **Tech stack**: Language, framework, runtime constraints. Existing conventions to follow?
4. **CI/CD assumption**: Assume in place unless user says otherwise. Confirm only if the request touches deployment.
5. **Manual validation**: Does this touch a UI? Major API surface changes? External integration impact? These will require manual review.
6. **Existing codebase**: Is this greenfield or modifying existing code? If existing, where does it live?
7. **Constraints**: Timeline, performance, security, compliance requirements?

## Output: Clarification Summary

After getting answers, produce a structured summary:

```
## Clarification Summary

**Request:** <one-sentence restatement>
**Scope:** <what's in, what's out>
**Success criteria:** <observable outcomes>
**Tech stack:** <languages, frameworks, versions>
**Manual validation required:** <yes/no, what triggers it>
**Assumptions confirmed:** <list of things user explicitly confirmed>
**Out of scope confirmed:** <list of things user explicitly excluded>
```

Ask the user: "Does this summary accurately capture your request? Confirm to proceed to planning."

**Do not proceed until user explicitly confirms.** Write the confirmed summary to memory under key `clarification_summary`.

## Rules

- Ask all questions in one message, organized by category
- Do not ask about things already stated in the initial request
- Every item in the summary must have been stated or confirmed by the user — no inferences
```

- [ ] **Step 2: Create `agents/jsf-clarifier.md`**

```markdown
---
name: jsf-clarifier
description: Runs the structured clarification dialogue for a new software request. Invoke when a new workflow starts and clarification_summary is not yet in memory.
---

You are the clarification specialist. Follow the `jsf-clarification` skill exactly.

1. Read the initial request from memory key `initial_request` (or from the user's message if not in memory).
2. Ask one organized batch of questions covering all applicable categories from the jsf-clarification skill.
3. Wait for the user's answers.
4. Produce a Clarification Summary.
5. Ask the user to explicitly confirm it.
6. Write the confirmed summary to memory: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write --key clarification_summary --value '<JSON-encoded summary>'`
```

- [ ] **Step 3: Commit**

```bash
git add skills/jsf-clarification/SKILL.md agents/jsf-clarifier.md
git commit -m "feat: add jsf-clarification skill and clarifier agent"
```

### Task 4.3: Spec/planning skill and agent

- [ ] **Step 1: Create `skills/jsf-spec-planning/SKILL.md`**

```markdown
# Spec and Planning

## Input

Read `clarification_summary` from memory. Do not begin without it.

## Technical Spec

Produce a document with these sections:

1. **Problem** — What is being solved and why
2. **Constraints** — Tech stack, performance, security, compliance
3. **Architecture** — How it fits into the existing system; new components and their responsibilities
4. **Data model changes** — New tables/schemas/fields, if any
5. **API surface** — New or changed endpoints/functions/interfaces
6. **Security considerations** — Auth, input validation, data exposure
7. **Manual validation triggers** — List each change type that requires manual review

## Implementation Plan

Ordered list of phases. Each phase:
- `name`: kebab-case identifier
- `description`: what it builds
- `tests_first`: what failing tests to write (specific function/class names)
- `files`: exact files to create or modify
- `parallel`: true if this phase can run concurrently with another (name which)
- `manual_validation`: true/false and trigger reason if true
- `commit_message`: the git commit message for when this phase is complete

## User Confirmation

Present both documents. Incorporate feedback. Do not write to memory until user explicitly confirms.

Write to memory:
- `spec_document` — the full spec
- `implementation_plan` — the confirmed plan as a JSON array of phase objects
```

- [ ] **Step 2: Create `agents/jsf-planner.md`**

```markdown
---
name: jsf-planner
description: Produces the technical spec and phased implementation plan after clarification is confirmed. Invoke after clarification_summary is in memory.
---

You are the technical planning specialist. Follow the `jsf-spec-planning` skill.

1. Read `clarification_summary` from memory.
2. Produce Technical Spec and Implementation Plan.
3. Present both to the user and incorporate feedback.
4. Write confirmed spec to memory: key `spec_document`
5. Write confirmed plan to memory: key `implementation_plan` (JSON array of phase objects)
```

- [ ] **Step 3: Commit**

```bash
git add skills/jsf-spec-planning/SKILL.md agents/jsf-planner.md
git commit -m "feat: add jsf-spec-planning skill and planner agent"
```

### Task 4.4: TDD implementation and code review

- [ ] **Step 1: Create `skills/jsf-tdd-implementation/SKILL.md`**

```markdown
# TDD Implementation

## Red-Green Discipline

For every unit of behavior:
1. Write a failing test that defines the expected behavior
2. Run it — confirm it fails with the right error (not a syntax error)
3. Write minimum code to make it pass
4. Run it — confirm it passes
5. Refactor if needed
6. Repeat for the next behavior

Do not write implementation code before the failing test exists. Do not proceed past a failing test.

## Phase Scope

Read your phase spec from memory (`implementation_plan`, find the matching phase by name). Implement only what is in that phase. If you discover scope that should be in another phase, write a note to memory under `scope_note:<phase_name>` and stop — do not expand scope.

## On Unexpected Failure

If a test fails unexpectedly (not the current TDD step), stop. Write to memory:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write \
  --key "unexpected_failure:<phase_name>" \
  --value '{"test":"<name>","error":"<message>","files_changed":["..."]}' \
  --tags "failure,needs_attention"
```
Then surface the failure to the user. Do not continue with other tests.

## Code Standards (applied before commit)

Every change must be checked by the reviewer agent before committing. The reviewer checks for:
- Hardcoded credentials or secrets (API keys, passwords, tokens in code)
- SQL/shell/XSS injection vectors (unsanitized inputs passed to queries or shell commands)
- Insecure defaults (debug mode left on, auth disabled, `0.0.0.0` binding without intent)
- Missing input validation at system boundaries (user input, external API responses)

Do not commit a phase until the reviewer approves it.
```

- [ ] **Step 2: Create `agents/jsf-implementer.md`**

```markdown
---
name: jsf-implementer
description: Implements a single phase of the plan using TDD. Invoke with the phase identifier. Reads phase spec from implementation_plan in memory.
---

You are the implementation specialist for one phase. Follow the `jsf-tdd-implementation` skill exactly.

1. Read `agent_context` from memory to get your phase name and trace ID.
2. Read `implementation_plan` from memory and find your phase.
3. For each behavior in the phase spec: write failing test, confirm failure, implement, confirm pass.
4. When all tests pass, write: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write --key "phase_complete:<phase_name>" --value '{"status":"ready_for_review","tests_pass":true}'`
```

- [ ] **Step 3: Create `agents/jsf-reviewer.md`**

```markdown
---
name: jsf-reviewer
description: Reviews code changes for security issues before phase commit. Invoke after phase_complete:<name> appears in memory.
---

You are the security and code quality reviewer. Check all changes since the last commit:

1. Search for hardcoded secrets: `grep -rE "(api_key|password|token|secret)\s*=\s*['\"][^'\"]{8,}" --include="*.py" --include="*.js" --include="*.ts" .`
2. Check for unparameterized queries: look for string concatenation into SQL strings
3. Check for shell injection: look for `subprocess.call(f"...{user_input}...")` patterns
4. Check for insecure defaults in config files

Write result to memory:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write \
  --key "review_result:<phase_name>" \
  --value '{"approved":true,"issues":[]}' \
  --tags "review"
```

If critical issues are found, set `"approved":false` and list each issue. Block the commit.
```

- [ ] **Step 4: Commit**

```bash
git add skills/jsf-tdd-implementation/SKILL.md agents/jsf-implementer.md agents/jsf-reviewer.md
git commit -m "feat: add TDD implementation skill, implementer and reviewer agents"
```

### Task 4.5: Validation gate skill and agent

- [ ] **Step 1: Create `skills/jsf-validation-gate/SKILL.md`**

```markdown
# Validation Gate

## Completion Criteria

A phase is complete when BOTH:
1. Automated tests pass (all tests in the phase's test suite green)
2. Manual validation confirmed, if required

A phase is NOT complete when only one criterion is met.

## Manual Validation Triggers

Manual validation is required for any of:
- UI changes (visual layout, user flows, interactive elements)
- Major API surface changes (new endpoints, changed request/response schemas)
- Changes affecting external integrations (webhooks, third-party APIs, data exports)
- Any change flagged in `manual_validation_triggers` in the project's `factory-config.json`

## Timing

Trigger manual validation requests as early as possible — before implementation of the next phase begins. If the next phase is independent (parallelizable), start it while waiting for manual confirmation.

## Confirmation

Manual validation must be explicitly confirmed by the user. Phrases like "looks good", "LGTM", or "confirmed" count. Silence or ambiguous responses do not count.

Write confirmation to memory:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write \
  --key "validation_confirmed:<phase_name>" \
  --value '{"confirmed_at":"<ISO8601>","by":"user","method":"manual|automated"}' \
  --tags "validation"
```
```

- [ ] **Step 2: Create `agents/jsf-validator.md`**

```markdown
---
name: jsf-validator
description: Runs the validation gate for a completed implementation phase. Checks automated tests and coordinates manual validation if needed.
---

You are the validation specialist. Follow the `jsf-validation-gate` skill.

1. Read `agent_context` from memory to get the phase name.
2. Run the phase's test suite. Report pass/fail counts.
3. Check the phase spec (`implementation_plan`) for `manual_validation: true`.
4. If manual validation is needed: surface the request to the user now. Do not wait.
5. When both criteria are met, write `validation_confirmed:<phase_name>` to memory.
```

- [ ] **Step 3: Commit**

```bash
git add skills/jsf-validation-gate/SKILL.md agents/jsf-validator.md
git commit -m "feat: add jsf-validation-gate skill and validator agent"
```

### Task 4.6: Commands

- [ ] **Step 1: Create `commands/jsf-start.md`**

```markdown
---
description: Start the software factory workflow for a new idea or feature request
---

You are beginning the John's Software Factory workflow. Use the `jsf-workflow` skill throughout.

1. If `$ARGUMENTS` is provided, write it to memory as `initial_request`. Otherwise ask the user to describe their request, then write it.
2. Call `gc` on memory to clear any expired entries from previous sessions.
3. Dispatch the clarifier agent to run the structured clarification dialogue.
4. Do not proceed to planning until `clarification_summary` is in memory.
```

- [ ] **Step 2: Create `commands/jsf-resume.md`**

```markdown
---
description: Resume a software factory workflow from the last memory checkpoint
---

Read factory memory: call `list-keys`, then fetch each relevant key.

Identify the most recent incomplete phase (exists in `implementation_plan` but lacks `validation_confirmed:<name>`).

Display current state to the user:
- Phases completed (with commit SHAs from memory)
- Phase currently in progress (if any)
- Next phase to start

Ask: "Ready to resume from <phase name>?" before proceeding.
```

- [ ] **Step 3: Create `commands/jsf-validate.md`**

```markdown
---
description: Run the validation gate for the current phase
---

Dispatch the validator agent for the current in-progress phase. The validator runs automated tests, reports results, and if manual validation is required per the `jsf-validation-gate` skill, prompts the user for explicit confirmation. Do not mark a phase complete until both criteria pass.
```

- [ ] **Step 4: Create `commands/jsf-status.md`**

```markdown
---
description: Show the current factory workflow state from memory
---

Read factory memory (`list-keys`, then relevant reads). Display:
- Project: `initial_request` summary
- Clarification: confirmed / pending
- Plan: number of phases, phase names
- Each phase: complete / in-progress / not-started, with commit SHA if complete
- Pending validations: any `phase_complete` without `validation_confirmed`
- Memory keys: count of live entries, file location
```

- [ ] **Step 5: Verify commands load**

```bash
claude --plugin-dir . --print "What slash commands does the jsf plugin provide?"
```
Expected: lists start, resume, validate, status.

- [ ] **Step 6: Run end-to-end smoke test**

```bash
export CLAUDE_PLUGIN_DATA=/tmp/sf-smoke-test
export CLAUDE_PLUGIN_ROOT=$(pwd)
rm -f /tmp/sf-smoke-test/memory.jsonl

claude --plugin-dir .
# In the session: /jsf:start Build a hello-world CLI tool in Python that greets by name
```
Expected: clarifier agent engages, asks organized batch of questions.

- [ ] **Step 7: Verify memory was written after confirmation**

```bash
CLAUDE_PLUGIN_DATA=/tmp/sf-smoke-test python3 scripts/memory.py read --key clarification_summary
```
Expected: non-null JSON object with clarification summary fields (not `null`).

- [ ] **Step 8: Commit**

```bash
git add commands/ agents/jsf-validator.md
git commit -m "feat: add all four factory commands and complete agent set"
```

---

## Sub-Plan 5: OpenTelemetry Monitoring

**Goal:** Emit OTLP traces for all factory work. One root trace per task; independent sub-traces per phase. Bi-directional linking: phase spans include an OTel Link to the root span at creation time (phase → root); the orchestrator emits a separate instantaneous "link event" span in the root trace context that records the child trace_id as an attribute (root → phase).

**Stateless design:** `telemetry.py` is a subprocess CLI tool. Every invocation is a fresh process — in-process span state does not survive between calls. All commands therefore create, record, and end spans immediately (they are "point-in-time event spans"). This is the correct approach for CLI-based OTel instrumentation. Duration is not tracked at the span level; the factory workflow's phase duration can be computed from the timestamp delta between `phase_started` and `phase_complete` event spans in the trace viewer.

**Files:**
- Create: `scripts/requirements.txt`
- Create: `scripts/telemetry.py`
- Create: `skills/jsf-otel-tracing/SKILL.md`
- Create: `tests/telemetry/test_telemetry.py`
- Modify: `hooks/hooks.json` (add SessionStart hook)

### Task 5.1: Dependencies

- [ ] **Step 1: Create `scripts/requirements.txt`**

```
opentelemetry-sdk>=1.24.0
opentelemetry-exporter-otlp-proto-grpc>=1.24.0
```

- [ ] **Step 2: Install dependencies**

```bash
pip install -r scripts/requirements.txt
```

- [ ] **Step 3: Commit**

```bash
git add scripts/requirements.txt
git commit -m "feat: add opentelemetry Python dependencies"
```

### Task 5.2: Telemetry script with tests

- [ ] **Step 1: Write failing tests**

Create `tests/telemetry/test_telemetry.py`:
```python
import subprocess, json, os
from pathlib import Path

# Run from repo root: python3 -m pytest tests/telemetry/test_telemetry.py -v
SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "telemetry.py"

def run(args, env=None):
    # SF_OTEL_ENABLED=0 disables OTLP export; span IDs are still generated and returned
    e = {**os.environ, **(env or {}), "SF_OTEL_ENABLED": "0"}
    return subprocess.run(["python3", str(SCRIPT)] + args, capture_output=True, text=True, env=e)

def test_start_root_returns_ids():
    r = run(["start-root", "--task", "test-task"])
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert "trace_id" in data and len(data["trace_id"]) == 32
    assert "span_id" in data and len(data["span_id"]) == 16

def test_start_root_is_stateless():
    """Two separate calls produce different span IDs (each invocation is a fresh span)."""
    r1 = run(["start-root", "--task", "task-a"])
    r2 = run(["start-root", "--task", "task-b"])
    d1, d2 = json.loads(r1.stdout), json.loads(r2.stdout)
    assert d1["span_id"] != d2["span_id"]
    assert d1["trace_id"] != d2["trace_id"]

def test_start_phase_returns_new_trace_id():
    r = run(["start-root", "--task", "test-task"])
    root = json.loads(r.stdout)
    r2 = run(["start-phase", "--phase", "planning",
               "--root-trace-id", root["trace_id"],
               "--root-span-id", root["span_id"]])
    assert r2.returncode == 0, r2.stderr
    phase = json.loads(r2.stdout)
    # Phase must have a DIFFERENT trace_id from root (independent trace)
    assert phase["trace_id"] != root["trace_id"]
    assert "span_id" in phase

def test_phase_link_points_to_root():
    """Phase span output includes the root trace_id it was linked to."""
    r = run(["start-root", "--task", "t"])
    root = json.loads(r.stdout)
    r2 = run(["start-phase", "--phase", "impl",
               "--root-trace-id", root["trace_id"],
               "--root-span-id", root["span_id"]])
    phase = json.loads(r2.stdout)
    assert phase["linked_root_trace_id"] == root["trace_id"]

def test_emit_forward_link():
    """emit-forward-link creates an instantaneous span in root trace context with child trace_id."""
    r = run(["start-root", "--task", "t"])
    root = json.loads(r.stdout)
    r2 = run(["start-phase", "--phase", "impl",
               "--root-trace-id", root["trace_id"],
               "--root-span-id", root["span_id"]])
    phase = json.loads(r2.stdout)
    r3 = run(["emit-forward-link",
               "--root-trace-id", root["trace_id"],
               "--root-span-id", root["span_id"],
               "--child-trace-id", phase["trace_id"],
               "--child-span-id", phase["span_id"],
               "--phase", "impl"])
    assert r3.returncode == 0
    result = json.loads(r3.stdout)
    assert result["span_name"] == "factory.phase_started"
    assert result["child_trace_id"] == phase["trace_id"]

def test_emit_event():
    r = run(["emit-event",
             "--trace-id", "a" * 32, "--parent-span-id", "b" * 16,
             "--name", "factory.validation", "--attrs", '{"result":"pass"}'])
    assert r.returncode == 0
    result = json.loads(r.stdout)
    assert result["span_name"] == "factory.validation"

def test_otel_disabled_still_returns_ids():
    """With SF_OTEL_ENABLED=0, no export happens but IDs are still valid."""
    r = run(["start-root", "--task", "no-export"], {"SF_OTEL_ENABLED": "0"})
    data = json.loads(r.stdout)
    assert len(data["trace_id"]) == 32
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
python3 -m pytest tests/telemetry/test_telemetry.py -v
```
Expected: `FileNotFoundError` since `scripts/telemetry.py` doesn't exist.

- [ ] **Step 3: Create `scripts/telemetry.py`**

```python
#!/usr/bin/env python3
"""
OTel span management for jsf. Stateless CLI — every invocation is a fresh process.
Each command creates an instantaneous "event span", ends it, and flushes before exiting.
Span IDs returned in stdout should be stored in memory.py for cross-call correlation.

Usage:
  telemetry.py start-root       --task NAME
  telemetry.py start-phase      --phase NAME --root-trace-id TID --root-span-id SID
  telemetry.py emit-forward-link --root-trace-id TID --root-span-id SID \
                                  --child-trace-id TID2 --child-span-id SID2 --phase NAME
  telemetry.py emit-event       --trace-id TID --parent-span-id SID --name NAME [--attrs JSON]

Bi-directional linking:
  phase → root: phase span includes an OTel Link to the root span at creation (start-phase)
  root → phase: emit-forward-link creates an instantaneous span IN the root trace context
                with the child trace_id as an attribute — visible in any trace viewer that
                follows the root trace_id

Set SF_OTEL_ENABLED=0 to disable OTLP export (tests/dry-run). IDs are still generated.
"""
import argparse, json, os, sys
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import SpanContext, TraceFlags, NonRecordingSpan, Link, StatusCode, use_span
from opentelemetry import context as otel_context, trace as otel_trace

ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
ENABLED = os.environ.get("SF_OTEL_ENABLED", "1") != "0"


def _make_provider(resource_attrs: dict) -> TracerProvider:
    resource = Resource.create({"service.name": "jsf", "service.version": "0.1.0",
                                **resource_attrs})
    provider = TracerProvider(resource=resource)
    if ENABLED:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        # SimpleSpanProcessor: exports each span synchronously before process exits
        provider.add_span_processor(SimpleSpanProcessor(
            OTLPSpanExporter(endpoint=ENDPOINT, insecure=True)
        ))
    return provider


def _ctx_from(trace_id_hex: str, span_id_hex: str) -> SpanContext:
    return SpanContext(
        trace_id=int(trace_id_hex, 16),
        span_id=int(span_id_hex, 16),
        is_remote=True,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )


def _span_ids(span) -> dict:
    ctx = span.get_span_context()
    return {"trace_id": format(ctx.trace_id, "032x"), "span_id": format(ctx.span_id, "016x")}


def cmd_start_root(args):
    """Emits a root 'factory.task' span. Returns trace_id and span_id for storage in memory."""
    provider = _make_provider({"factory.task": args.task})
    tracer = provider.get_tracer("jsf")
    # No parent = new TraceID
    with tracer.start_as_current_span("factory.task",
                                      attributes={"factory.task.name": args.task}) as span:
        ids = _span_ids(span)
    # Span is ended on __exit__; SimpleSpanProcessor exports it synchronously
    print(json.dumps(ids))


def cmd_start_phase(args):
    """
    Emits a 'factory.phase' span in a NEW independent trace, with an OTel Link to root (phase → root).
    Returns the new trace_id + span_id. Store in memory for emit-forward-link.
    """
    provider = _make_provider({"factory.phase": args.phase})
    tracer = provider.get_tracer("jsf")
    root_link = Link(
        context=_ctx_from(args.root_trace_id, args.root_span_id),
        attributes={"link.type": "root_trace", "factory.phase.name": args.phase}
    )
    # start_span with no parent context = generates a new TraceID (independent trace)
    with tracer.start_as_current_span("factory.phase", links=[root_link],
                                      attributes={"factory.phase.name": args.phase}) as span:
        ids = _span_ids(span)
    print(json.dumps({**ids, "linked_root_trace_id": args.root_trace_id}))


def cmd_emit_forward_link(args):
    """
    Emits an instantaneous 'factory.phase_started' span WITHIN the root trace (using root
    trace_id + root span_id as the parent context). This records the child trace_id as an
    attribute visible when browsing the root trace — completing the bi-directional link.
    """
    provider = _make_provider({"factory.task": "link-recorder"})
    tracer = provider.get_tracer("jsf")
    root_ctx = _ctx_from(args.root_trace_id, args.root_span_id)
    # Use the root span context as parent so this span appears inside the root trace
    parent_ctx = otel_trace.set_span_in_context(NonRecordingSpan(root_ctx))
    with tracer.start_as_current_span(
        "factory.phase_started",
        context=parent_ctx,
        attributes={
            "factory.phase.name": args.phase,
            "link.child_trace_id": args.child_trace_id,
            "link.child_span_id": args.child_span_id,
            "link.type": "child_phase",
        }
    ) as span:
        ids = _span_ids(span)
    print(json.dumps({"span_name": "factory.phase_started",
                      "child_trace_id": args.child_trace_id, **ids}))


def cmd_emit_event(args):
    """
    Emits an instantaneous named span within an existing trace context.
    Use for checkpoints, validation results, and other discrete factory events.
    """
    provider = _make_provider({"factory.event": args.name})
    tracer = provider.get_tracer("jsf")
    parent_ctx_obj = _ctx_from(args.trace_id, args.parent_span_id)
    parent_ctx = otel_trace.set_span_in_context(NonRecordingSpan(parent_ctx_obj))
    attrs = json.loads(args.attrs) if args.attrs else {}
    with tracer.start_as_current_span(args.name, context=parent_ctx,
                                      attributes=attrs) as span:
        ids = _span_ids(span)
    print(json.dumps({"span_name": args.name, **ids}))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")

    sr = sub.add_parser("start-root"); sr.add_argument("--task", required=True)

    sp = sub.add_parser("start-phase")
    sp.add_argument("--phase", required=True)
    sp.add_argument("--root-trace-id", required=True)
    sp.add_argument("--root-span-id", required=True)

    fl = sub.add_parser("emit-forward-link")
    fl.add_argument("--root-trace-id", required=True)
    fl.add_argument("--root-span-id", required=True)
    fl.add_argument("--child-trace-id", required=True)
    fl.add_argument("--child-span-id", required=True)
    fl.add_argument("--phase", required=True)

    ev = sub.add_parser("emit-event")
    ev.add_argument("--trace-id", required=True)
    ev.add_argument("--parent-span-id", required=True)
    ev.add_argument("--name", required=True)
    ev.add_argument("--attrs")

    args = p.parse_args()
    dispatch = {
        "start-root": cmd_start_root, "start-phase": cmd_start_phase,
        "emit-forward-link": cmd_emit_forward_link, "emit-event": cmd_emit_event,
    }
    if args.cmd in dispatch:
        dispatch[args.cmd](args)
    else:
        p.print_help(); sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
python3 -m pytest tests/telemetry/test_telemetry.py -v
```
Expected: all 5 tests pass.

- [ ] **Step 5: Verify OTLP export (no Docker needed)**

```bash
# Option A: confirm data is sent (no collector needed — connection refused is expected, but we verify the attempt)
SF_OTEL_ENABLED=1 python3 scripts/telemetry.py start-root --task "smoke-test" 2>&1
```
Expected: stdout returns JSON with `trace_id` and `span_id`. Stderr may show a gRPC connection error if no collector is running — that is expected and only means the export attempt failed, not that the code is broken.

```bash
# Option B: full trace visualization with Jaeger (requires Docker)
docker run -d --name jaeger -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one
SF_OTEL_ENABLED=1 python3 scripts/telemetry.py start-root --task "integration-test"
# Open http://localhost:16686 → Service: jsf → should show factory.task span
```

- [ ] **Step 6: Create `skills/jsf-otel-tracing/SKILL.md`**

```markdown
# OpenTelemetry Tracing

## Overview

Factory work emits OTLP traces to `http://localhost:4317` (configurable via `OTEL_EXPORTER_OTLP_ENDPOINT`).

Set `SF_OTEL_ENABLED=0` to disable export without breaking anything (useful in tests).

## Trace Architecture

- **Root trace**: one per factory task. Spans the full workflow. Stored in memory as `main_trace_id` + `main_span_id`.
- **Phase sub-traces**: one independent trace per phase. Links back to root (phase → root via OTel Link). Root logs child trace IDs as events (`factory.phase_started`) for forward traceability (root → phase).

## Stateless Design

Every `telemetry.py` call is a fresh process. Each command creates an instantaneous span, ends it, and exports it before exit (using `SimpleSpanProcessor`). No state is held in memory between calls. Returned IDs are stored in `memory.py` for cross-call correlation.

## Orchestrator Protocol

```bash
# At task start: emit root span, store IDs
ROOT=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/telemetry.py" start-root --task "feature-name")
ROOT_TRACE=$(echo "$ROOT" | python3 -c "import sys,json; print(json.load(sys.stdin)['trace_id'])")
ROOT_SPAN=$(echo "$ROOT" | python3 -c "import sys,json; print(json.load(sys.stdin)['span_id'])")
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write --key main_trace_id --value "\"${ROOT_TRACE}\""
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write --key main_span_id --value "\"${ROOT_SPAN}\""

# When starting a phase: emit phase span (independent trace, links back to root)
PHASE=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/telemetry.py" start-phase \
  --phase "planning" --root-trace-id "${ROOT_TRACE}" --root-span-id "${ROOT_SPAN}")
PHASE_TRACE=$(echo "$PHASE" | python3 -c "import sys,json; print(json.load(sys.stdin)['trace_id'])")
PHASE_SPAN=$(echo "$PHASE" | python3 -c "import sys,json; print(json.load(sys.stdin)['span_id'])")

# Emit forward link: instantaneous span in root trace recording child trace_id (root → phase)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/telemetry.py" emit-forward-link \
  --root-trace-id "${ROOT_TRACE}" --root-span-id "${ROOT_SPAN}" \
  --child-trace-id "${PHASE_TRACE}" --child-span-id "${PHASE_SPAN}" --phase "planning"

# Store phase context in memory
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write --key "phase_trace:planning" --value "\"${PHASE_TRACE}\""
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/memory.py" write --key "phase_span:planning" --value "\"${PHASE_SPAN}\""

# Emit a discrete factory event within a trace
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/telemetry.py" emit-event \
  --trace-id "${PHASE_TRACE}" --parent-span-id "${PHASE_SPAN}" \
  --name "factory.validation" --attrs '{"result":"pass","tests_run":42}'
```

## Key Span Names

| Span | When |
|------|------|
| `factory.task` | Full workflow duration (root trace) |
| `factory.phase` | Each implementation phase (sub-trace) |
| `factory.validation.automated` | After running test suite |
| `factory.validation.manual` | After user manual confirmation |
| `factory.checkpoint` | After git commit checkpoint |
```

- [ ] **Step 7: Add SessionStart hook to `hooks/hooks.json`**

Add to the `"hooks"` object:
```json
"SessionStart": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "[ -z \"${OTEL_EXPORTER_OTLP_ENDPOINT}\" ] && export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317; [ -z \"${SF_OTEL_ENABLED}\" ] && export SF_OTEL_ENABLED=1; true",
        "async": true
      }
    ]
  }
]
```

- [ ] **Step 8: Commit**

```bash
git add scripts/telemetry.py skills/jsf-otel-tracing/SKILL.md tests/telemetry/ hooks/hooks.json
git commit -m "feat: add OpenTelemetry monitoring with root/sub-trace and bi-directional links"
```

---

## Sub-Plan 6: Cursor Support

**Goal:** Cursor IDE compatibility via `.cursor-plugin/plugin.json` and `.mdc` rule files. Hooks are shared — `hooks/hooks.json` is referenced from both manifests. Rules mirror skill content with Cursor frontmatter.

**Note on hooks sharing:** Cursor uses the same `hooks/hooks.json` format as Claude Code. The Cursor manifest references the same hooks directory. The bash scripts in `hooks/scripts/` work in both IDEs since both call them via shell.

**Files:**
- Create: `.cursor-plugin/plugin.json`
- Create: `rules/jsf-workflow.mdc`
- Create: `rules/jsf-clarification.mdc`
- Create: `rules/jsf-spec-planning.mdc`
- Create: `rules/jsf-tdd-implementation.mdc`
- Create: `rules/jsf-validation-gate.mdc`
- Create: `rules/jsf-memory-protocol.mdc`
- Create: `rules/jsf-otel-tracing.mdc`

### Task 6.1: Cursor manifest

- [ ] **Step 1: Create `.cursor-plugin/plugin.json`**

```json
{
  "name": "jsf",
  "version": "0.1.0",
  "description": "John's Software Factory — takes projects from idea to implementation via phased, validated workflow.",
  "author": { "name": "jmeagher" },
  "license": "MIT",
  "hooks": "hooks/hooks.json"
}
```

- [ ] **Step 2: Commit**

```bash
git add .cursor-plugin/plugin.json
git commit -m "feat: add Cursor plugin manifest with hooks reference"
```

### Task 6.2: Cursor rules (.mdc files)

Each `.mdc` file has YAML frontmatter and the corresponding skill's content (copy of the skill, not a symlink — symlinks are not reliably resolved in all Cursor environments).

- [ ] **Step 1: Create `rules/jsf-workflow.mdc`** (copy content from `skills/jsf-workflow/SKILL.md` with added frontmatter)

```markdown
---
description: Software factory master workflow — orchestrates all phases from intake to validation
globs: ["**/*"]
alwaysApply: false
---

[content from skills/jsf-workflow/SKILL.md — copy verbatim]
```

- [ ] **Step 2: Create `rules/jsf-clarification.mdc`**

```markdown
---
description: Software factory clarification — structured Q&A before planning begins
globs: ["**/*"]
alwaysApply: false
---

[content from skills/jsf-clarification/SKILL.md — copy verbatim]
```

- [ ] **Step 3: Create `rules/jsf-spec-planning.mdc`**

```markdown
---
description: Software factory spec and planning — technical spec and phased implementation plan
globs: ["**/*"]
alwaysApply: false
---

[content from skills/jsf-spec-planning/SKILL.md — copy verbatim]
```

- [ ] **Step 4: Create `rules/jsf-tdd-implementation.mdc`**

```markdown
---
description: Software factory TDD implementation — red-green discipline and code standards
globs: ["**/*"]
alwaysApply: false
---

[content from skills/jsf-tdd-implementation/SKILL.md — copy verbatim]
```

- [ ] **Step 5: Create `rules/jsf-validation-gate.mdc`**

```markdown
---
description: Software factory validation gate — phase completion criteria and manual validation
globs: ["**/*"]
alwaysApply: false
---

[content from skills/jsf-validation-gate/SKILL.md — copy verbatim]
```

- [ ] **Step 6: Create `rules/jsf-memory-protocol.mdc`**

```markdown
---
description: Software factory memory protocol — how agents read and write shared state
globs: ["**/*"]
alwaysApply: false
---

[content from skills/jsf-memory-protocol/SKILL.md — copy verbatim]
```

- [ ] **Step 7: Create `rules/jsf-otel-tracing.mdc`**

```markdown
---
description: Software factory OpenTelemetry tracing — root trace, phase sub-traces, bi-directional links
globs: ["**/*"]
alwaysApply: false
---

[content from skills/jsf-otel-tracing/SKILL.md — copy verbatim]
```

- [ ] **Step 8: Commit**

```bash
git add rules/
git commit -m "feat: add Cursor .mdc rules for all factory skills"
```

---

## Verification: End-to-End Test

Run after all sub-plans are complete (from repo root):

**1. All hook tests pass:**
```bash
bash tests/hooks/test-dangerous-bash.sh && \
bash tests/hooks/test-dangerous-git.sh && \
bash tests/hooks/test-dangerous-sql.sh
```

**2. Memory system tests pass:**
```bash
python3 -m pytest tests/memory/test_memory.py -v
```

**3. Telemetry tests pass:**
```bash
python3 -m pytest tests/telemetry/test_telemetry.py -v
```

**4. Full workflow smoke test:**
```bash
export CLAUDE_PLUGIN_DATA=/tmp/sf-e2e-test
export CLAUDE_PLUGIN_ROOT=$(pwd)
rm -f /tmp/sf-e2e-test/memory.jsonl

claude --plugin-dir .
# In session: /jsf:start Build a hello-world CLI in Python that greets by name
```
Expected: clarifier agent asks structured batch of questions.

After confirming clarification in the session:
```bash
# Verify memory was written
CLAUDE_PLUGIN_DATA=/tmp/sf-e2e-test python3 scripts/memory.py read --key clarification_summary
```
Expected: non-null JSON with fields including `request`, `scope`, `tech_stack` (not `null`).

**5. Memory state inspection:**
```bash
CLAUDE_PLUGIN_DATA=/tmp/sf-e2e-test python3 scripts/memory.py list-keys
```
Expected: JSON object showing at minimum `initial_request` and `clarification_summary` keys.

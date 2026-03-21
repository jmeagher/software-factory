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

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

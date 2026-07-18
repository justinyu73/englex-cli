#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
fixture="$repo_root/tests/fixtures/naer-computing-15275.csv"
evidence="$repo_root/tests/fixtures/naer-computing-15275-evidence.json"

python3 - "$fixture" "$evidence" <<'PY'
import csv
import hashlib
import json
import sys
from pathlib import Path

fixture = Path(sys.argv[1])
evidence = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
payload = fixture.read_bytes()
digest = hashlib.sha256(payload).hexdigest()
if digest != evidence["sha256"]:
    raise SystemExit(f"snapshot digest mismatch: {digest}")

with fixture.open(encoding="utf-8-sig", newline="") as handle:
    reader = csv.DictReader(handle)
    if reader.fieldnames != evidence["observed_columns"]:
        raise SystemExit(f"snapshot columns mismatch: {reader.fieldnames}")
    rows = list(reader)

if len(rows) != evidence["row_count"]:
    raise SystemExit(f"snapshot row count mismatch: {len(rows)}")
if any(not row["英文名稱"].strip() for row in rows):
    raise SystemExit("snapshot contains a blank English term")

print(f"NAER computing frozen snapshot smoke passed: {len(rows)} rows, sha256 {digest}")
PY

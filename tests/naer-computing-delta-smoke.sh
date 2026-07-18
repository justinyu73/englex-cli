#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
fixture="$repo_root/tests/fixtures/naer-computing-15275.csv"
evidence="$repo_root/tests/fixtures/naer-computing-15275-evidence.json"
baseline="$repo_root/tests/fixtures/naer-computing-15275-authority-baseline.json"
expected="$repo_root/tests/fixtures/naer-computing-15275-delta.json"

sh "$repo_root/tests/naer-computing-snapshot-smoke.sh"

python3 - "$fixture" "$evidence" "$baseline" "$expected" "${1:-}" <<'PY'
import csv
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

fixture_path = Path(sys.argv[1])
evidence_path = Path(sys.argv[2])
baseline_path = Path(sys.argv[3])
expected_path = Path(sys.argv[4])
mode = sys.argv[5]


def normalize(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
canonical = {}
aliases = {}
for entry in baseline["entries"]:
    canonical.setdefault(normalize(entry["term"]), entry["term"])
    for alias in entry.get("aliases", []):
        aliases.setdefault(normalize(alias), entry["term"])

with fixture_path.open(encoding="utf-8-sig", newline="") as handle:
    rows = list(csv.DictReader(handle))

groups = defaultdict(list)
for row_number, row in enumerate(rows, start=1):
    term = row["英文名稱"].strip()
    groups[normalize(term)].append({"source_row": row_number, "term": term})

duplicates = []
canonical_matches = []
alias_conflicts = []
unmapped = []
for normalized, source_rows in groups.items():
    first = source_rows[0]
    if len(source_rows) > 1:
        duplicates.append({"term": first["term"], "source_rows": [item["source_row"] for item in source_rows]})
    elif normalized in canonical:
        canonical_matches.append({"term": first["term"], "existing_term": canonical[normalized]})
    elif normalized in aliases:
        alias_conflicts.append({"term": first["term"], "existing_term": aliases[normalized]})
    else:
        unmapped.append(first)

delta = {
    "snapshot_sha256": evidence["sha256"],
    "normalization": "Unicode NFKC, casefold, and ASCII/Unicode whitespace collapse on English labels",
    "summary": {
        "source_rows": len(rows),
        "unique_source_terms": len(groups),
        "duplicate_groups": len(duplicates),
        "duplicate_rows": sum(len(item["source_rows"]) - 1 for item in duplicates),
        "canonical_matches": len(canonical_matches),
        "alias_conflicts": len(alias_conflicts),
        "unmapped": len(unmapped),
    },
    "duplicate_terms": duplicates,
    "canonical_matches": canonical_matches,
    "alias_conflicts": alias_conflicts,
    "new_terms": unmapped,
}

if mode == "--write-expected":
    expected_path.write_text(json.dumps(delta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
elif mode:
    raise SystemExit("usage: sh tests/naer-computing-delta-smoke.sh [--write-expected]")
else:
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    if delta != expected:
        raise SystemExit("NAER computing delta mismatch; rerun only after an approved new intake")
    print(
        "NAER computing delta smoke passed: "
        f"duplicate_groups={delta['summary']['duplicate_groups']}, "
        f"duplicate_rows={delta['summary']['duplicate_rows']}, "
        f"canonical_matches={delta['summary']['canonical_matches']}, "
        f"alias_conflicts={delta['summary']['alias_conflicts']}, "
        f"unmapped={delta['summary']['unmapped']}"
    )
PY

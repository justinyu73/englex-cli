#!/usr/bin/env sh
set -eu

python3 - <<'PY'
import json
from pathlib import Path

source = json.loads(Path("tests/fixtures/gen-ai-glossary-terms.json").read_text(encoding="utf-8"))
expected = json.loads(Path("tests/fixtures/gen-ai-glossary-delta.json").read_text(encoding="utf-8"))
baseline = json.loads(Path("tests/fixtures/gen-ai-glossary-authority-baseline.json").read_text(encoding="utf-8"))
if baseline["source_commit"] != expected["source_commit"]:
    raise SystemExit("baseline does not match the pinned source commit")
identifiers = set(baseline["identifiers"])
delta = [
    {
        "term": item["term"],
        "aliases": item.get("aliases", []),
        "category": item["category"],
    }
    for item in source
    if item["term"].strip().casefold() not in identifiers
    and not any(alias.strip().casefold() in identifiers for alias in item.get("aliases", []))
]

if not delta:
    raise SystemExit("expected a non-empty glossary delta")
if delta != expected["terms"]:
    raise SystemExit(f"delta mismatch: {delta!r}")
print(json.dumps(delta, ensure_ascii=False, indent=2))
PY

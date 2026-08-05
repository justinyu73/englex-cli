#!/bin/sh
set -eu

python3 - <<'PY'
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from englex import cli
from englex.data import GRANDFATHERED_TRUST_TERMS, TRUST_LEVELS, seed_entries, validate_entries, validate_local_data

if TRUST_LEVELS != {"maintainer_verified", "community", "ai_drafted", "legacy"}:
    raise SystemExit(f"unexpected trust-level enum: {TRUST_LEVELS!r}")

drafts = json.loads(Path("tests/fixtures/naer-computing-n3b-draft-entries.json").read_text(encoding="utf-8"))
# Independently rederive each shipped trust level from its provenance/attribution,
# so a mislabelled entry fails: legacy provenance -> legacy; an attributed upgrade
# -> community/maintainer_verified; any other sourced/no_public_source entry -> ai_drafted.
for entry in seed_entries():
    kind = entry["provenance"]["kind"]
    if kind == "legacy":
        expected = {"legacy"}
    elif "attribution" in entry:
        expected = {"community", "maintainer_verified"}
    else:
        expected = {"ai_drafted"}
    if entry["trust_level"] not in expected:
        raise SystemExit(f"{entry['term']}: expected {expected}, got {entry['trust_level']}")

if {entry["trust_level"] for entry in drafts} != {"ai_drafted"}:
    raise SystemExit("N3b entries must retain ai_drafted until trust is explicitly upgraded")

for index, level in enumerate(sorted(TRUST_LEVELS)):
    entry = {
        "schema_version": 2,
        "term": f"trust smoke {index}",
        "aliases": [],
        "status": "常用",
        "provenance": {"version": 1, "kind": "sourced", "source_url": "https://example.com/source"},
        "trust_level": level,
        "senses": [{"domain": "測試", "definition": "信任等級 smoke"}],
    }
    if level in {"community", "maintainer_verified"}:
        entry["attribution"] = {
            "kind": "upgrade",
            "upgraded_by": "smoke maintainer",
            "evidence": "https://example.com/review",
            "date": "2026-07-14",
        }
    if validate_entries([entry], "trust_smoke"):
        raise SystemExit(f"{level}: valid trust level rejected")

for level in ("community", "maintainer_verified"):
    missing_attribution = {
        "schema_version": 2,
        "term": f"missing attribution {level}",
        "aliases": [],
        "status": "常用",
        "provenance": {"version": 1, "kind": "sourced", "source_url": "https://example.com/source"},
        "trust_level": level,
        "senses": [{"domain": "測試", "definition": "信任等級 smoke"}],
    }
    if not any("trust upgrade requires attribution" in error for error in validate_entries([missing_attribution], "trust_smoke")):
        raise SystemExit(f"{level}: missing attribution was accepted")

for level in ("ai_drafted", "legacy"):
    no_attribution = {
        "schema_version": 2,
        "term": f"no attribution {level}",
        "aliases": [],
        "status": "常用",
        "provenance": {"version": 1, "kind": "sourced", "source_url": "https://example.com/source"},
        "trust_level": level,
        "senses": [{"domain": "測試", "definition": "信任等級 smoke"}],
    }
    if validate_entries([no_attribution], "trust_smoke"):
        raise SystemExit(f"{level}: attribution should be optional")

grandfathered = {
    "schema_version": 2,
    "term": "sdcv",
    "aliases": [],
    "status": "常用",
    "provenance": {"version": 1, "kind": "sourced", "source_url": "https://example.com/source"},
    "trust_level": "maintainer_verified",
    "attribution": {"kind": "grandfathered", "note": "原始 seed,無正式升級紀錄"},
    "senses": [{"domain": "測試", "definition": "信任等級 smoke"}],
}
if validate_entries([grandfathered], "seed"):
    raise SystemExit("grandfathered seed attribution was rejected")
if GRANDFATHERED_TRUST_TERMS != {entry["term"] for entry in seed_entries() if entry.get("attribution", {}).get("kind") == "grandfathered"}:
    raise SystemExit("grandfathered trust-term manifest differs from shipped seed")

missing = dict(entry)
missing.pop("trust_level")
invalid = dict(entry, trust_level="not_a_level")
if sum("invalid trust_level" in error for error in validate_entries([missing, invalid], "trust_smoke")) != 2:
    raise SystemExit("trust-level schema does not reject missing and invalid values")
if validate_local_data():
    raise SystemExit("shipped local data does not validate")

terminal = StringIO()
with redirect_stdout(terminal):
    if cli.main(["scan", "canary deployment"]) != 0:
        raise SystemExit("terminal scan failed")
if "信任等級：legacy（既有隨附，未回溯驗證）" not in terminal.getvalue():
    raise SystemExit("terminal scan does not display legacy trust level")

json_output = StringIO()
with redirect_stdout(json_output):
    if cli.main(["scan", "--json", "sdcv"]) != 0:
        raise SystemExit("JSON scan failed")
payload = json.loads(json_output.getvalue())
if payload["results"][0]["entry"]["trust_level"] != "maintainer_verified":
    raise SystemExit("JSON scan does not include the trust level")

print("trust-level smoke passed: schema enum and terminal/JSON scan labels verified")
PY

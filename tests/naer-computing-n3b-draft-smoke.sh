#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

python3 - "$repo_root" <<'PY'
import csv
import json
import sys
import unicodedata
from pathlib import Path

from englex.data import seed_entries, validate_entries, validate_local_data

root = Path(sys.argv[1])
draft_path = root / "tests/fixtures/naer-computing-n3b-draft-entries.json"
delta_path = root / "tests/fixtures/naer-computing-15275-delta.json"
snapshot_path = root / "tests/fixtures/naer-computing-15275.csv"
catalog_url = "https://data.gov.tw/dataset/15275"
expected_terms = [
    "authentication",
    "data encryption",
    "public key",
    "private key",
    "certificate",
    "credentials",
    "cipher",
    "secure channel",
    "vulnerability",
    "end to end encryption",
    "distributed processing",
    "fault tolerance",
    "replication",
    "deadlock",
    "transaction processing",
    "concurrent processes",
    "availability",
    "consistency",
    "Transmission Control Protocol/Internet Protocol; TCP/IP",
    "address resolution protocol，ARP",
    "network protocol",
    "proxy server",
    "topology",
    "streaming",
    "schema",
    "data model",
    "relational model",
    "primary key",
    "partition",
    "information retrieval(IR)",
]


def normalize(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


drafts = json.loads(draft_path.read_text(encoding="utf-8"))
if [entry["term"] for entry in drafts] != expected_terms:
    raise SystemExit("N3b draft terms do not match the approved source-term selection")

delta = json.loads(delta_path.read_text(encoding="utf-8"))
delta_terms = {normalize(item["term"]): item for item in delta["new_terms"]}
with snapshot_path.open(encoding="utf-8-sig", newline="") as handle:
    source_rows = {normalize(row["英文名稱"]): row for row in csv.DictReader(handle)}

for entry in drafts:
    key = normalize(entry["term"])
    if key not in delta_terms:
        raise SystemExit(f"{entry['term']}: not an N2 unmapped source term")
    if entry["provenance"] != {"version": 1, "kind": "sourced", "source_url": catalog_url}:
        raise SystemExit(f"{entry['term']}: unexpected provenance")
    source_label = source_rows[key]["中文名稱"].strip()
    for sense in entry["senses"]:
        definition = sense["definition"].strip()
        if not any("\u4e00" <= char <= "\u9fff" for char in definition):
            raise SystemExit(f"{entry['term']}: definition must contain Traditional-Chinese text")
        if definition == source_label:
            raise SystemExit(f"{entry['term']}: definition must not copy the NAER Chinese label")

seed = seed_entries()
seed_by_term = {entry["term"]: entry for entry in seed}
for draft in drafts:
    if seed_by_term.get(draft["term"]) != draft:
        raise SystemExit(f"{draft['term']}: curated seed entry differs from the accepted draft")
base_seed = [entry for entry in seed if entry["term"] not in {draft["term"] for draft in drafts}]
errors = validate_entries(drafts, "naer_n3b_draft")
# base_seed are shipped seed entries (grandfathered dispensation applies), merged
# with ai_drafted candidates in one call so cross-list canonical/alias dups are caught.
errors.extend(validate_entries([*base_seed, *drafts], "seed", allow_legacy=True))
errors.extend(validate_local_data())
if errors:
    raise SystemExit("\n".join(errors))

print(f"NAER computing N3b draft smoke passed: {len(drafts)} sourced entries are identical in curated seed")
PY

#!/usr/bin/env sh
set -eu

python3 - <<'PY'
import json
from pathlib import Path

from englex.data import seed_entries, validate_entries, validate_local_data

source = json.loads(Path("tests/fixtures/gen-ai-glossary-terms.json").read_text(encoding="utf-8"))
delta = json.loads(Path("tests/fixtures/gen-ai-glossary-delta.json").read_text(encoding="utf-8"))
drafts = json.loads(Path("tests/fixtures/gen-ai-glossary-draft-entries.json").read_text(encoding="utf-8"))

source_by_term = {item["term"].casefold(): item for item in source}
expected_terms = [item["term"].casefold() for item in delta["terms"]]
draft_terms = [item["term"].casefold() for item in drafts]
if draft_terms != expected_terms:
    raise SystemExit(f"draft terms do not match delta: {draft_terms!r}")

seed = seed_entries()
seed_by_term = {entry["term"].casefold(): entry for entry in seed}
draft_terms = {entry["term"].casefold() for entry in drafts}
for draft in drafts:
    seeded = seed_by_term.get(draft["term"].casefold())
    if seeded is not None and seeded != draft:
        raise SystemExit(f"{draft['term']}: seeded entry differs from reviewed draft")

base_seed = [entry for entry in seed if entry["term"].casefold() not in draft_terms]
# These drafts are asserted above to equal their shipped seed entries, so they carry
# seed's grandfathered dispensation; validate them (and the merge) under "seed".
errors = validate_entries(drafts, "seed")
errors.extend(validate_entries([*base_seed, *drafts], "seed", allow_legacy=True))
errors.extend(validate_local_data())
if errors:
    raise SystemExit("\n".join(errors))

for entry in drafts:
    source_item = source_by_term[entry["term"].casefold()]
    if entry["provenance"]["source_url"] != delta["source_url"]:
        raise SystemExit(f"{entry['term']}: unexpected provenance URL")
    for sense in entry["senses"]:
        if not any("\u4e00" <= char <= "\u9fff" for char in sense["definition"]):
            raise SystemExit(f"{entry['term']}: definition must contain original Traditional-Chinese text")
        if sense["definition"] == source_item["definition"]:
            raise SystemExit(f"{entry['term']}: definition must not copy source text")

print(json.dumps(drafts, ensure_ascii=False, indent=2))
PY

python3 -B -m englex validate-data

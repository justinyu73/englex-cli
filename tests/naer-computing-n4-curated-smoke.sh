#!/bin/sh
set -eu

python3 - <<'PY'
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from englex import cli
from englex.core import lookup
from englex.data import seed_entries, validate_entries

drafts = json.loads(Path("tests/fixtures/naer-computing-n3b-draft-entries.json").read_text(encoding="utf-8"))
seed = seed_entries()
seed_by_term = {entry["term"]: entry for entry in seed}
if len(drafts) != 30:
    raise SystemExit("N4 expects exactly 30 accepted NAER entries")
for draft in drafts:
    if seed_by_term.get(draft["term"]) != draft:
        raise SystemExit(f"{draft['term']}: seed entry is not the accepted draft")
    if draft["trust_level"] != "ai_drafted":
        raise SystemExit(f"{draft['term']}: trust level must remain ai_drafted")
    if draft["provenance"] != {"version": 1, "kind": "sourced", "source_url": "https://data.gov.tw/dataset/15275"}:
        raise SystemExit(f"{draft['term']}: NAER provenance changed")

errors = validate_entries(seed, "seed", allow_legacy=True)
if errors:
    raise SystemExit("\n".join(errors))

for term in ("authentication", "private key", "deadlock", "TCP/IP", "primary key"):
    result = lookup(term, allow_fallback=False, include_overlay=False)
    if len(result) != 1 or result[0]["trust_level"] != "ai_drafted":
        raise SystemExit(f"{term}: curated lookup regression")

terminal = StringIO()
with redirect_stdout(terminal):
    if cli.main(["scan", "authentication TCP/IP ARP schema"]) != 0:
        raise SystemExit("N4 terminal scan failed")
if terminal.getvalue().count("信任等級：ai_drafted（AI 草擬，未經人工審定）") != 4:
    raise SystemExit("N4 terminal scan did not display ai_drafted for every selected result")

print("NAER computing N4 curated smoke passed: 30 ai_drafted entries are shipped and lookupable")
PY

#!/usr/bin/env sh
set -eu

python3 - <<'PY'
import json
from pathlib import Path

from englex.data import seed_entries

drafts = json.loads(Path("tests/fixtures/gen-ai-glossary-draft-entries.json").read_text(encoding="utf-8"))
seed_by_term = {entry["term"].casefold(): entry for entry in seed_entries()}
for draft in drafts:
    if seed_by_term.get(draft["term"].casefold()) != draft:
        raise SystemExit(f"{draft['term']}: approved draft is not present in curated seed")
PY

python3 -B -m englex validate-data
python3 -B -m englex lookup --exact orchestration | grep -F 'LLM／代理／工作流' >/dev/null
python3 -B -m englex lookup --exact 'LLM orchestration' | grep -F 'orchestration' >/dev/null

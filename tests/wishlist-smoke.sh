#!/usr/bin/env sh
set -eu

data_home="$(mktemp -d)"
trap 'rm -rf "$data_home"' EXIT

XDG_DATA_HOME="$data_home" python3 -B -m englex wishlist add "wishlist manual add"
XDG_DATA_HOME="$data_home" python3 -B -m englex wishlist add "WISHLIST   MANUAL ADD"
XDG_DATA_HOME="$data_home" python3 -B -m englex wishlist list --json > "$data_home/wishlist-manual-list.json"
XDG_DATA_HOME="$data_home" python3 -B - <<'PY'
import json
import os
from pathlib import Path

data_home = Path(os.environ["XDG_DATA_HOME"])
payload = json.loads((data_home / "englex" / "wishlist.json").read_text(encoding="utf-8"))
if payload != {"enabled": False, "terms": ["wishlist manual add"]}:
    raise SystemExit(f"manual add did not create a term-only, deduplicated payload: {payload!r}")
listed = json.loads((data_home / "wishlist-manual-list.json").read_text(encoding="utf-8"))
if listed != {"schema_version": 2, "enabled": False, "terms": ["wishlist manual add"], "pending_new": 1}:
    raise SystemExit(f"manual add list returned unexpected payload: {listed!r}")
if set(payload) != {"enabled", "terms"}:
    raise SystemExit(f"manual add stored fields other than enabled and terms: {payload!r}")
PY

XDG_DATA_HOME="$data_home" python3 -B -m englex wishlist disable
XDG_DATA_HOME="$data_home" python3 -B -m englex wishlist add "wishlist manual while disabled"
XDG_DATA_HOME="$data_home" python3 -B -m englex wishlist add "daemon" > "$data_home/wishlist-curated-add.txt"
grep -F "已在詞庫，補批會跳過" "$data_home/wishlist-curated-add.txt"
XDG_DATA_HOME="$data_home" python3 -B - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads((Path(os.environ["XDG_DATA_HOME"]) / "englex" / "wishlist.json").read_text(encoding="utf-8"))
if payload != {"enabled": False, "terms": ["wishlist manual add", "wishlist manual while disabled", "daemon"]}:
    raise SystemExit(f"manual add was affected by disabled state or did not retain curated term: {payload!r}")
PY

if XDG_DATA_HOME="$data_home" python3 -B -m englex lookup "wishlist smoke miss"; then
  echo "wishlist smoke miss unexpectedly resolved" >&2
  exit 1
fi
XDG_DATA_HOME="$data_home" python3 -B - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads((Path(os.environ["XDG_DATA_HOME"]) / "englex" / "wishlist.json").read_text(encoding="utf-8"))
if payload != {"enabled": False, "terms": ["wishlist manual add", "wishlist manual while disabled", "daemon"]}:
    raise SystemExit(f"disabled automatic miss changed wishlist: {payload!r}")
PY

XDG_DATA_HOME="$data_home" python3 -B -m englex wishlist enable
if XDG_DATA_HOME="$data_home" python3 -B -m englex lookup "wishlist smoke miss"; then
  echo "wishlist smoke miss unexpectedly resolved" >&2
  exit 1
fi
XDG_DATA_HOME="$data_home" python3 -B -m englex scan "wishlist smoke miss in a selected line" >/dev/null

XDG_DATA_HOME="$data_home" python3 -B - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads((Path(os.environ["XDG_DATA_HOME"]) / "englex" / "wishlist.json").read_text(encoding="utf-8"))
if payload != {"enabled": True, "terms": ["wishlist manual add", "wishlist manual while disabled", "daemon", "wishlist smoke miss"]}:
    raise SystemExit(f"unexpected wishlist payload: {payload!r}")
if any(key in payload for key in ("input", "context", "history", "timestamp")):
    raise SystemExit("wishlist stored query context or history")
PY

XDG_DATA_HOME="$data_home" python3 -B -m englex wishlist list --json > "$data_home/wishlist-list.json"
XDG_DATA_HOME="$data_home" python3 -B - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads((Path(os.environ["XDG_DATA_HOME"]) / "wishlist-list.json").read_text(encoding="utf-8"))
if payload != {"schema_version": 2, "enabled": True, "terms": ["wishlist manual add", "wishlist manual while disabled", "daemon", "wishlist smoke miss"], "pending_new": 3}:
    raise SystemExit(f"wishlist list returned unexpected payload: {payload!r}")
PY

XDG_DATA_HOME="$data_home" python3 -B -m englex wishlist list > "$data_home/wishlist-pending-three.txt"
grep -F "淨新待補 3 個（可手動觸發補批：tools/wishlist_draft.py brief）" "$data_home/wishlist-pending-three.txt"

XDG_DATA_HOME="$data_home" python3 -B -m englex wishlist add "wishlist smoke batch one" >/dev/null
XDG_DATA_HOME="$data_home" python3 -B -m englex wishlist add "wishlist smoke batch two" >/dev/null
XDG_DATA_HOME="$data_home" python3 -B -m englex wishlist list > "$data_home/wishlist-pending-five.txt"
grep -F "淨新待補 5 個（可手動觸發補批：tools/wishlist_draft.py brief）" "$data_home/wishlist-pending-five.txt"
XDG_DATA_HOME="$data_home" python3 -B -m englex wishlist clear --yes
XDG_DATA_HOME="$data_home" python3 -B - <<'PY'
import json
import os
from pathlib import Path

payload = json.loads((Path(os.environ["XDG_DATA_HOME"]) / "englex" / "wishlist.json").read_text(encoding="utf-8"))
if payload != {"enabled": True, "terms": []}:
    raise SystemExit(f"wishlist clear did not preserve only opt-in state: {payload!r}")
PY

if grep -E '^(from|import) (socket|urllib|http\.client|requests|asyncio)' englex/data.py englex/cli.py; then
  echo "wishlist implementation introduced a networking import" >&2
  exit 1
fi

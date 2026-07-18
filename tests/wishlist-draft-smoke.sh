#!/usr/bin/env sh
set -eu

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
seed="$work/seed_data.json"
wl="$work/wishlist.json"
cp englex/seed_data.json "$seed"

# wishlist: one pending term + one already-curated term (daemon is in the shipped seed)
printf '%s\n' '{"enabled": true, "terms": ["wishlist smoke newterm", "daemon"]}' > "$wl"

python3 -B - "$seed" "$wl" "$work" <<'PY'
import json, subprocess, sys
seed, wl, work = sys.argv[1], sys.argv[2], sys.argv[3]

def run(*args, expect=0):
    p = subprocess.run([sys.executable, "-B", "tools/wishlist_draft.py", *args],
                       capture_output=True, text=True)
    if p.returncode != expect:
        raise SystemExit(f"{args} -> rc={p.returncode} (expected {expect})\n{p.stderr}")
    return p.stdout

before = json.load(open(seed, encoding="utf-8"))
n0 = len(before["entries"])

# 1) brief: pending listed, already-curated skipped
brief = run("brief", "--seed", seed, "--wishlist", wl)
if "wishlist smoke newterm" not in brief:
    raise SystemExit("brief 未列出待草擬詞")
if "已收錄" not in brief or "daemon" not in brief:
    raise SystemExit("brief 未把已收錄的 daemon 標為跳過")

# 2) merge a valid ai_drafted draft -> append-only + prune wishlist
draft = work + "/draft.json"
json.dump([{
    "schema_version": 2, "term": "wishlist smoke newterm", "aliases": [], "status": "常用",
    "senses": [{"domain": "測試", "definition": "補批 smoke 用的原創解釋。",
                "context_triggers": ["alpha", "beta"], "context_required": False}],
    "provenance": {"version": 1, "kind": "no_public_source", "reason": "smoke 測試，無公開來源。"},
    "trust_level": "ai_drafted",
}], open(draft, "w", encoding="utf-8"), ensure_ascii=False)
run("merge", draft, "--seed", seed, "--wishlist", wl)

after = json.load(open(seed, encoding="utf-8"))
if len(after["entries"]) != n0 + 1:
    raise SystemExit("merge 未 append 恰一條")
if after["entries"][:n0] != before["entries"]:
    raise SystemExit("merge 破壞了既有 entries（非 append-only）")
if after["entries"][-1]["term"] != "wishlist smoke newterm":
    raise SystemExit("新詞未在尾端")
remaining = json.load(open(wl, encoding="utf-8"))["terms"]
if "wishlist smoke newterm" in remaining or "daemon" not in remaining:
    raise SystemExit(f"wishlist prune 錯誤：{remaining}")

# 3) reject non-ai_drafted
bad = work + "/bad.json"
json.dump([dict(json.load(open(draft, encoding="utf-8"))[0], term="another term",
               trust_level="maintainer_verified")],
          open(bad, "w", encoding="utf-8"), ensure_ascii=False)
run("merge", bad, "--seed", seed, "--wishlist", wl, expect=1)

# 4) reject duplicate canonical (canary already shipped)
dup = work + "/dup.json"
json.dump([dict(json.load(open(draft, encoding="utf-8"))[0], term="canary")],
          open(dup, "w", encoding="utf-8"), ensure_ascii=False)
run("merge", dup, "--seed", seed, "--wishlist", wl, expect=1)

print("wishlist-draft smoke passed: brief 去重、merge append-only+prune、拒 non-ai_drafted、拒 dup")
PY

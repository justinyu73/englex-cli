#!/usr/bin/env python3
"""Dev-time Chain C batch tool (never shipped in the wheel).

Two commands bracket an offline AI drafting step (the AI is the maintainer's own
codex/Claude session, never englex runtime):

  brief  — read the local wishlist, drop terms already curated, emit a codex-ready
           drafting brief for the pending terms.
  merge  — take the drafted ai_drafted fixture back, validate it, append-only into
           seed_data.json (surgical, preserving file style), and prune the merged
           terms from the wishlist so it stays a live "still-todo" list.

No network, no subprocess, no LLM call here. englex runtime stays offline.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from englex.data import validate_entries, validate_local_data  # noqa: E402

SEED = os.path.join(os.path.dirname(__file__), "..", "englex", "seed_data.json")


def default_wishlist():
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "englex", "wishlist.json")


def glossary_names(seed_path):
    d = json.load(open(seed_path, encoding="utf-8"))
    names = set()
    for e in d["entries"]:
        names.add(e["term"].lower())
        for a in e.get("aliases", []):
            names.add(a.lower())
    for t in d.get("legacy_terms", []):
        names.add((t if isinstance(t, str) else t.get("term", "")).lower())
    names.discard("")
    return names


def cmd_brief(args):
    wl_path = args.wishlist or default_wishlist()
    if not os.path.exists(wl_path):
        print(f"# wishlist 不存在：{wl_path}", file=sys.stderr)
        return 1
    terms = json.load(open(wl_path, encoding="utf-8")).get("terms", [])
    known = glossary_names(args.seed)
    pending = [t for t in terms if t.lower() not in known]
    covered = [t for t in terms if t.lower() in known]

    out = [
        "# Chain C 補批 brief（給 codex/AI 草擬）",
        "",
        f"來源 wishlist：`{wl_path}`（{len(terms)} 詞，{len(covered)} 已收錄跳過，{len(pending)} 待草擬）",
        "",
        "## 規則（違反即失敗）",
        "- 每詞草擬一個 entry，`trust_level` **必須** `ai_drafted`。",
        "- `senses`：原創繁中工程解釋、`domain`、`context_triggers`、`context_required`；多義項給多個 sense。",
        "- `provenance`：`no_public_source`+非空 reason，或 `sourced`+合法 HTTPS `source_url`。**不要捏造 URL**。",
        "- schema 照既有 entry（`schema_version:2`、`aliases`、`status` ∈ {常用/需判讀/安全風險/安全原則}）。",
        "- 輸出成 JSON 陣列存檔，再 `python3 tools/wishlist_draft.py merge <檔>`。",
        "",
        "## 待草擬詞",
    ]
    out += [f"- `{t}`" for t in pending] or ["（無：wishlist 的詞都已收錄）"]
    if covered:
        out += ["", "## 已收錄（跳過）", *[f"- `{t}`" for t in covered]]
    print("\n".join(out))
    return 0


def cmd_merge(args):
    new_entries = json.load(open(args.fixture, encoding="utf-8"))
    if not isinstance(new_entries, list) or not new_entries:
        print("fixture 必須是非空的 entry 陣列", file=sys.stderr)
        return 1

    # Chain B invariant: batch drafts are ai_drafted only.
    bad = [e.get("term") for e in new_entries if e.get("trust_level") != "ai_drafted"]
    if bad:
        print(f"只接受 ai_drafted，違反：{bad}", file=sys.stderr)
        return 1

    errors = validate_entries(new_entries, "wishlist_draft")
    if errors:
        print("草稿驗證失敗：\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1

    existing = glossary_names(args.seed)
    dups = [e["term"] for e in new_entries
            if e["term"].lower() in existing
            or any(a.lower() in existing for a in e.get("aliases", []))]
    if dups:
        print(f"與既有詞庫 canonical/alias 撞名，拒絕：{dups}", file=sys.stderr)
        return 1

    raw = open(args.seed, encoding="utf-8").read()
    cut = raw.rindex("\n  ]")          # close of the entries array
    additions = "".join(
        ",\n    " + json.dumps(e, ensure_ascii=False, separators=(",", ":"))
        for e in new_entries
    )
    merged = raw[:cut] + additions + raw[cut:]

    parsed = json.loads(merged)        # must stay valid JSON
    open(args.seed, "w", encoding="utf-8").write(merged)

    # New entries are validated above; existing entries are untouched (surgical
    # append). validate_local_data re-checks the shipped seed after a real merge;
    # for a temp --seed (smoke) it is benign and the smoke asserts the temp result.
    if os.path.abspath(args.seed) == os.path.abspath(SEED):
        local_errors = validate_local_data()
        if local_errors:
            open(args.seed, "w", encoding="utf-8").write(raw)   # roll back
            print("併入後 validate_local_data 失敗，已回滾：\n  " + "\n  ".join(local_errors), file=sys.stderr)
            return 1

    merged_terms = {e["term"].lower() for e in new_entries}
    pruned = 0
    wl_path = args.wishlist or default_wishlist()
    if os.path.exists(wl_path):
        wl = json.load(open(wl_path, encoding="utf-8"))
        before = len(wl.get("terms", []))
        wl["terms"] = [t for t in wl.get("terms", []) if t.lower() not in merged_terms]
        pruned = before - len(wl["terms"])
        json.dump(wl, open(wl_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"併入 {len(new_entries)} 條 ai_drafted（詞庫 entries → {len(parsed['entries'])}）；"
          f"wishlist 清掉 {pruned} 個已收錄詞。")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("brief")
    b.add_argument("--wishlist")
    b.add_argument("--seed", default=SEED)
    b.set_defaults(func=cmd_brief)
    m = sub.add_parser("merge")
    m.add_argument("fixture")
    m.add_argument("--wishlist")
    m.add_argument("--seed", default=SEED)
    m.set_defaults(func=cmd_merge)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

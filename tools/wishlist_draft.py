#!/usr/bin/env python3
"""Dev-time Chain C batch tool (never shipped in the wheel).

Three commands bracket the maintainer's offline-from-runtime AI drafting step:

  brief  — read the local wishlist, drop terms already curated, emit a codex-ready
           drafting brief for the pending terms (no network).
  merge  — take a drafted ai_drafted fixture, validate it, append-only into
           seed_data.json (surgical, preserving file style), and prune the merged
           terms from the wishlist.
  auto   — manual trigger, no threshold: when the wishlist has any net-new
           terms, call the Claude API to draft ai_drafted entries for them,
           then run the same validate/merge/prune path as `merge`. The
           maintainer alone decides when a batch is worth running.

`auto` is a maintainer curation step, not englex runtime: it calls an online model
with the maintainer's own key. The shipped tool's lookup runtime stays fully
offline — this tool is never packaged in the wheel. See product-feature-map.md.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from englex.data import validate_entries, validate_local_data  # noqa: E402

SEED = os.path.join(os.path.dirname(__file__), "..", "englex", "seed_data.json")
DRAFT_MODEL = "claude-opus-5"

# Statuses the curated schema uses; constrain the model so it can't invent one.
STATUS_ENUM = ["常用", "需判讀", "安全風險", "安全原則"]


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


def pending_terms(wl_path, seed_path):
    """Wishlist terms not yet present as a canonical term or alias in the glossary."""
    terms = json.load(open(wl_path, encoding="utf-8")).get("terms", [])
    known = glossary_names(seed_path)
    return [t for t in terms if t.lower() not in known], terms


def _merge_new_entries(new_entries, seed_path, wl_path):
    """Validate, surgically append-only into the seed, and prune the wishlist.

    Shared by `merge` (fixture-sourced) and `auto` (model-sourced) so both paths
    enforce the same ai_drafted-only, no-dup, rollback-on-failure guarantees.
    """
    if not isinstance(new_entries, list) or not new_entries:
        print("沒有可併入的 entry", file=sys.stderr)
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

    existing = glossary_names(seed_path)
    dups = [e["term"] for e in new_entries
            if e["term"].lower() in existing
            or any(a.lower() in existing for a in e.get("aliases", []))]
    if dups:
        print(f"與既有詞庫 canonical/alias 撞名，拒絕：{dups}", file=sys.stderr)
        return 1

    raw = open(seed_path, encoding="utf-8").read()
    cut = raw.rindex("\n  ]")          # close of the entries array
    additions = "".join(
        ",\n    " + json.dumps(e, ensure_ascii=False, separators=(",", ":"))
        for e in new_entries
    )
    merged = raw[:cut] + additions + raw[cut:]

    parsed = json.loads(merged)        # must stay valid JSON
    open(seed_path, "w", encoding="utf-8").write(merged)

    # New entries are validated above; existing entries are untouched (surgical
    # append). validate_local_data re-checks the shipped seed after a real merge;
    # for a temp --seed (smoke) it is benign and the smoke asserts the temp result.
    if os.path.abspath(seed_path) == os.path.abspath(SEED):
        local_errors = validate_local_data()
        if local_errors:
            open(seed_path, "w", encoding="utf-8").write(raw)   # roll back
            print("併入後 validate_local_data 失敗，已回滾：\n  " + "\n  ".join(local_errors), file=sys.stderr)
            return 1

    merged_terms = {e["term"].lower() for e in new_entries}
    pruned = 0
    if os.path.exists(wl_path):
        wl = json.load(open(wl_path, encoding="utf-8"))
        before = len(wl.get("terms", []))
        wl["terms"] = [t for t in wl.get("terms", []) if t.lower() not in merged_terms]
        pruned = before - len(wl["terms"])
        json.dump(wl, open(wl_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"併入 {len(new_entries)} 條 ai_drafted（詞庫 entries → {len(parsed['entries'])}）；"
          f"wishlist 清掉 {pruned} 個已收錄詞。")
    return 0


def cmd_brief(args):
    wl_path = args.wishlist or default_wishlist()
    if not os.path.exists(wl_path):
        print(f"# wishlist 不存在：{wl_path}", file=sys.stderr)
        return 1
    pending, terms = pending_terms(wl_path, args.seed)
    covered = [t for t in terms if t not in pending]

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
    wl_path = args.wishlist or default_wishlist()
    return _merge_new_entries(new_entries, args.seed, wl_path)


def _load_dotenv():
    """Populate ANTHROPIC_API_KEY from the repo-root .env if not already set.

    Matches the repo convention of keeping secrets in .env (never committed).
    Minimal KEY=VALUE parse; environment always wins.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.exists(env_path):
        return
    for line in open(env_path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _draft_schema():
    sense = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "domain": {"type": "string"},
            "definition": {"type": "string"},
            "context_triggers": {"type": "array", "items": {"type": "string"}},
            "context_required": {"type": "boolean"},
        },
        "required": ["domain", "definition", "context_triggers", "context_required"],
    }
    entry = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "schema_version": {"const": 2},
            "term": {"type": "string"},
            "aliases": {"type": "array", "items": {"type": "string"}},
            "status": {"type": "string", "enum": STATUS_ENUM},
            "senses": {"type": "array", "items": sense},
            "provenance": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "version": {"const": 1},
                    "kind": {"const": "no_public_source"},
                    "reason": {"type": "string"},
                },
                "required": ["version", "kind", "reason"],
            },
            "trust_level": {"const": "ai_drafted"},
        },
        "required": ["schema_version", "term", "aliases", "status", "senses", "provenance", "trust_level"],
    }
    return {
        "type": "object", "additionalProperties": False,
        "properties": {"entries": {"type": "array", "items": entry}},
        "required": ["entries"],
    }


_SYSTEM = (
    "你是 englex 的繁體中文工程術語 curator。把使用者給的英文工程／AI 術語，草擬成 curated glossary entry。"
    "規則：解釋是原創的繁中『工程語意』（這個詞在工程脈絡下代表什麼），不是字面翻譯；"
    "同一詞在不同脈絡有多義項時給多個 sense，各自帶 domain、判讀用的 context_triggers 與 context_required；"
    "status 從 {常用,需判讀,安全風險,安全原則} 擇一；trust_level 一律 ai_drafted；"
    "provenance 一律 no_public_source 並在 reason 說明這是 AI 草擬、未經人工審定、需人工複核；"
    "不得捏造來源或 URL。只輸出 schema 指定的 JSON。"
)


def _translate_pending(pending, model):
    _load_dotenv()
    try:
        import anthropic
    except ImportError:
        raise SystemExit("此命令需要 anthropic SDK（dev-time only）：pip install anthropic")

    client = anthropic.Anthropic()  # resolves ANTHROPIC_API_KEY or an `ant auth` profile
    user = "把這些工程術語各草擬成一個 entry：\n" + "\n".join(f"- {t}" for t in pending)
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=16000,
            system=_SYSTEM,
            output_config={"format": {"type": "json_schema", "schema": _draft_schema()}},
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.AuthenticationError:
        raise SystemExit("找不到 API 憑證：設定 .env 的 ANTHROPIC_API_KEY 或先跑 `ant auth login`")

    if resp.stop_reason == "refusal":
        raise SystemExit("翻譯被安全分類器拒絕（stop_reason=refusal），未併入任何詞條")
    text = next((b.text for b in resp.content if b.type == "text"), None)
    if text is None:
        raise SystemExit("模型未回傳文字內容，未併入任何詞條")
    return json.loads(text).get("entries", [])


def cmd_auto(args):
    wl_path = args.wishlist or default_wishlist()
    if not os.path.exists(wl_path):
        print(f"wishlist 不存在：{wl_path}", file=sys.stderr)
        return 1
    pending, _ = pending_terms(wl_path, args.seed)
    if not pending:
        print("沒有淨新待補詞，不觸發 AI 翻譯。")
        return 0
    print(f"淨新待補 {len(pending)} 個：以 {args.model} 草擬 AI 翻譯……")
    entries = _translate_pending(pending, args.model)
    return _merge_new_entries(entries, args.seed, wl_path)


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
    a = sub.add_parser("auto")
    a.add_argument("--wishlist")
    a.add_argument("--seed", default=SEED)
    a.add_argument("--model", default=DRAFT_MODEL)
    a.set_defaults(func=cmd_auto)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

"""Command-line interface. Core commands perform no networking or shell execution."""

import argparse
import json
import sys

from .core import QueryError, explain_lookup, find, format_card, format_scan, lookup, normalize, scan_line, validate_query
from .data import (
    PROVENANCE_VERSION,
    SCHEMA_VERSION,
    clear_wishlist,
    local_source_layers,
    raw_user_entries,
    record_wishlist_miss,
    record_wishlist_term,
    save_user_entries,
    set_wishlist_enabled,
    user_entries,
    validate_local_data,
    wishlist_enabled,
    wishlist_terms,
)
from .ecdict import EcdictError, import_csv
from .sdcv import SdcvError, lookup as sdcv_lookup


def _parser():
    parser = argparse.ArgumentParser(prog="englex", description="離線英語工程術語查詢")
    sub = parser.add_subparsers(dest="command")
    lookup_parser = sub.add_parser("lookup", help="精確術語或別名查詢")
    lookup_parser.add_argument("terms", nargs="+", metavar="TERM")
    lookup_parser.add_argument("--json", action="store_true", dest="json_output")
    lookup_parser.add_argument("--explain", action="store_true")
    match_mode = lookup_parser.add_mutually_exclusive_group()
    match_mode.add_argument("--no-fuzzy", action="store_true")
    match_mode.add_argument("--exact", action="store_true", help="只接受 canonical 或 alias 的精確匹配")
    lookup_parser.add_argument("--no-fallback", action="store_true", help="不使用已安裝的一般詞典 fallback")
    lookup_parser.add_argument("--curated-only", action="store_true", help="只查隨附 curated glossary；不讀 private overlay 或 ECDICT")
    find_parser = sub.add_parser("find", help="本機前綴搜尋")
    find_parser.add_argument("prefix")
    find_parser.add_argument("--json", action="store_true", dest="json_output")
    find_parser.add_argument("--explain", action="store_true")
    scan_parser = sub.add_parser("scan", help="明示掃描一行選取文字中的本機工程術語")
    scan_parser.add_argument("line", metavar="SELECTED_LINE")
    scan_parser.add_argument("--json", action="store_true", dest="json_output")
    scan_parser.add_argument("--format", choices=("concise", "expanded"), default="expanded")
    sub.add_parser("add", help="以互動提示新增私人術語")
    private_parser = sub.add_parser("private", help="明示管理本機 private overlay")
    private_sub = private_parser.add_subparsers(dest="private_command", required=True)
    private_list_parser = private_sub.add_parser("list", help="明示列出私人詞條")
    private_list_parser.add_argument("--json", action="store_true", dest="json_output")
    private_remove_parser = private_sub.add_parser("remove", help="刪除 canonical 完全相符的私人詞條")
    private_remove_parser.add_argument("term", metavar="TERM")
    private_remove_parser.add_argument("--yes", action="store_true", required=True, help="確認刪除私人詞條")
    private_add_parser = private_sub.add_parser("add", help="明示新增私人詞條；可由 scan 結果預填術語")
    private_add_parser.add_argument("--term", required=True, metavar="TERM")
    private_add_parser.add_argument("--abbreviation", metavar="SHORT")
    private_add_parser.add_argument("--full-name", metavar="FULL_NAME")
    private_add_parser.add_argument("--display-name", metavar="NAME")
    private_add_parser.add_argument("--abbreviation-kind", metavar="KIND", default="private_abbreviation")
    wishlist_parser = sub.add_parser("wishlist", help="明示管理本機 miss wishlist；預設關，不記查詢歷史")
    wishlist_sub = wishlist_parser.add_subparsers(dest="wishlist_command", required=True)
    wishlist_sub.add_parser("enable", help="開啟本機 miss wishlist 記錄")
    wishlist_sub.add_parser("disable", help="停止記錄新的本機 miss")
    wishlist_add_parser = wishlist_sub.add_parser("add", help="明示加入一個本機 wishlist 術語")
    wishlist_add_parser.add_argument("term", metavar="TERM")
    wishlist_list_parser = wishlist_sub.add_parser("list", help="列出本機 miss wishlist")
    wishlist_list_parser.add_argument("--json", action="store_true", dest="json_output")
    wishlist_clear_parser = wishlist_sub.add_parser("clear", help="清空本機 miss wishlist")
    wishlist_clear_parser.add_argument("--yes", action="store_true", required=True, help="確認清空 wishlist")
    export_parser = sub.add_parser("export", help="輸出可分享的使用者詞條")
    export_parser.add_argument("--shareable-only", action="store_true", required=True)
    sub.add_parser("validate-data", help="驗證本機詞彙資料 schema")
    sources_parser = sub.add_parser("sources", help="顯示本機資料層狀態，不顯示詞條內容")
    sources_parser.add_argument("--json", action="store_true", dest="json_output")
    import_parser = sub.add_parser("import-ecdict", help="匯入明示指定的本機 ECDICT CSV 基底")
    import_parser.add_argument("csv_path", metavar="CSV_PATH")
    sdcv_parser = sub.add_parser("lookup-sdcv", help="明示使用指定目錄中的本機 StarDict")
    sdcv_parser.add_argument("--data-dir", required=True, metavar="PATH", help="包含 dic/ 的 StarDict 資料根目錄")
    sdcv_parser.add_argument("terms", nargs="+", metavar="TERM")
    sdcv_parser.add_argument("--json", action="store_true", dest="json_output")
    return parser


def _ask(label, required=True):
    value = input(label).strip()
    if required and not value:
        raise QueryError("此欄位不可空白；未寫入任何資料。")
    return value


def _private_names(entry):
    aliases = entry.get("aliases", [])
    names = [entry.get("term"), *(aliases if isinstance(aliases, list) else [])]
    abbreviation = entry.get("abbreviation")
    if isinstance(abbreviation, dict):
        names.extend([abbreviation.get("short"), abbreviation.get("full_name")])
    return {normalize(name) for name in names if isinstance(name, str) and name.strip()}


def _add(prefilled_term=None, abbreviation=None):
    print("新增私人詞條（Ctrl-C 可取消）。")
    term = prefilled_term if prefilled_term is not None else _ask("術語：")
    aliases_text = _ask("別名（以逗號分隔，可留白）：", required=False)
    entry = {
        "schema_version": SCHEMA_VERSION,
        "term": validate_query(term),
        "aliases": [item.strip() for item in aliases_text.split(",") if item.strip()],
        "domain": _ask("領域："),
        "definition": _ask("繁中釋義："),
        "status": _ask("狀態（例如：常用／團隊用語）："),
        "shareable": _ask("允許匯出分享？輸入 yes 才允許 [no]：", required=False).casefold() == "yes",
        "provenance": {"version": PROVENANCE_VERSION, "kind": "private"},
        "trust_level": "community",
        "senses": [],
    }
    entry["senses"] = [{
        "domain": entry.pop("domain"),
        "definition": entry.pop("definition"),
    }]
    if abbreviation:
        short = abbreviation.get("short", "").strip()
        full_name = abbreviation.get("full_name", "").strip()
        if not short or not full_name:
            raise QueryError("私人縮寫需要明示短寫與已審定全稱；未寫入任何資料。")
        entry["abbreviation"] = {
            "short": short,
            "full_name": full_name,
            "display_name": abbreviation.get("display_name", short).strip() or short,
            "kind": abbreviation.get("kind", "private_abbreviation").strip() or "private_abbreviation",
        }
    entries = raw_user_entries()
    existing_names = set().union(*(_private_names(existing) for existing in entries))
    conflicts = _private_names(entry).intersection(existing_names)
    if conflicts:
        raise QueryError(f"私人詞條名稱衝突：{sorted(conflicts)[0]}；未寫入任何資料。")
    entries.append(entry)
    save_user_entries(entries)
    print("已寫入私人 overlay。")


def _show(entries, json_output=False, explanations=None, explain=False):
    if not entries:
        print("找不到本機詞條。", file=sys.stderr)
        return 1
    if json_output:
        payload = {"schema_version": SCHEMA_VERSION, "results": entries}
        if explanations is not None:
            payload["explanations"] = explanations
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    cards = []
    for index, entry in enumerate(entries):
        card = format_card(entry)
        if explain and explanations:
            explanation = explanations[index]
            card += f"\n查詢說明：第 {explanation['rank']} 位；{explanation['match']}"
        cards.append(card)
    print("\n\n".join(cards))
    return 0


def _show_private(entries, json_output=False):
    """Show private entries only after an explicit private-management command."""
    if json_output:
        print(json.dumps({"schema_version": SCHEMA_VERSION, "results": entries}, ensure_ascii=False, indent=2))
        return 0
    if not entries:
        print("沒有私人詞條。")
        return 0
    print("\n\n".join(format_card(entry) for entry in entries))
    return 0


def _remove_private(term):
    """Remove canonical-exact private entries without broad alias matching."""
    needle = normalize(validate_query(term))
    entries = raw_user_entries()
    remaining = [
        entry for entry in entries
        if not isinstance(entry.get("term"), str) or normalize(entry["term"]) != needle
    ]
    if len(remaining) == len(entries):
        print("找不到 canonical 完全相符的私人詞條；未寫入任何資料。", file=sys.stderr)
        return 1
    save_user_entries(remaining)
    print("已刪除私人詞條。")
    return 0


def _show_wishlist(json_output=False):
    """Show the explicit local wishlist without exposing any query context."""
    terms = wishlist_terms()
    pending_new = sum(
        not lookup(
            term,
            allow_inflection=False,
            allow_fuzzy=False,
            allow_fallback=False,
            include_overlay=False,
        )
        for term in terms
    )
    if json_output:
        print(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "enabled": wishlist_enabled(),
            "terms": terms,
            "pending_new": pending_new,
        }, ensure_ascii=False, indent=2))
        return 0
    if not terms:
        print("沒有 wishlist 詞條。")
    else:
        print("\n".join(terms))
    if pending_new > 0:
        print(f"淨新待補 {pending_new} 個（可手動觸發補批：tools/wishlist_draft.py brief）")
    else:
        print("沒有淨新待補詞")
    return 0


def _add_wishlist_term(term):
    """Explicitly queue one term, regardless of automatic-miss opt-in state."""
    term = validate_query(term)
    already_in_glossary = lookup(
        term,
        allow_inflection=False,
        allow_fuzzy=False,
        allow_fallback=False,
    )
    record_wishlist_term(term, require_enabled=False)
    if already_in_glossary:
        print("已在詞庫，補批會跳過")
    else:
        print("已加入本機 wishlist。")
    return 0


def _record_default_lookup_miss(query, entries, args):
    """Keep wishlist writes opt-in and limited to ordinary complete lookup misses."""
    if entries or args.exact or args.no_fuzzy or args.no_fallback or args.curated_only:
        return
    record_wishlist_miss(normalize(validate_query(query)))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        commands = {"lookup", "find", "scan", "add", "private", "wishlist", "export", "validate-data", "sources", "import-ecdict", "lookup-sdcv"}
        if argv and argv[0] not in commands and argv[0] not in {"-h", "--help"}:
            query = " ".join(argv)
            entries = lookup(query)
            if not entries:
                record_wishlist_miss(normalize(validate_query(query)))
            return _show(entries)
        args = _parser().parse_args(argv)
        if args.command == "add":
            _add()
            return 0
        if args.command == "private":
            if args.private_command == "list":
                return _show_private(user_entries(), args.json_output)
            if args.private_command == "add":
                if bool(args.abbreviation) != bool(args.full_name):
                    raise QueryError("私人縮寫必須同時提供 --abbreviation 與 --full-name；未寫入任何資料。")
                abbreviation = None if not args.abbreviation else {
                    "short": args.abbreviation,
                    "full_name": args.full_name,
                    "display_name": args.display_name or args.abbreviation,
                    "kind": args.abbreviation_kind,
                }
                _add(prefilled_term=args.term, abbreviation=abbreviation)
                return 0
            return _remove_private(args.term)
        if args.command == "wishlist":
            if args.wishlist_command == "enable":
                set_wishlist_enabled(True)
                print("這是你的個人 wishlist，本機、預設關、可清。")
                return 0
            if args.wishlist_command == "disable":
                set_wishlist_enabled(False)
                print("已停止記錄新的本機 wishlist miss。")
                return 0
            if args.wishlist_command == "add":
                return _add_wishlist_term(args.term)
            if args.wishlist_command == "list":
                return _show_wishlist(args.json_output)
            clear_wishlist()
            print("已清空本機 wishlist。")
            return 0
        if args.command == "export":
            shareable = [entry for entry in user_entries() if entry.get("shareable")]
            print(json.dumps(shareable, ensure_ascii=False, indent=2))
            return 0
        if args.command == "validate-data":
            errors = validate_local_data()
            if errors:
                print("\n".join(errors), file=sys.stderr)
                return 1
            print("資料驗證通過。")
            return 0
        if args.command == "sources":
            payload = local_source_layers()
            if args.json_output:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                for layer in payload["layers"]:
                    print(f"{layer['id']}: {layer['state']}")
            return 0
        if args.command == "import-ecdict":
            count = import_csv(args.csv_path)
            print(f"已匯入 {count} 個 ECDICT 一般詞典詞條。")
            return 0
        if args.command == "lookup-sdcv":
            return _show(sdcv_lookup(" ".join(args.terms), args.data_dir), args.json_output)
        if args.command == "find":
            entries = find(args.prefix)
            explanations = explain_lookup(args.prefix, include_prefix=True) if args.json_output or args.explain else None
            return _show(entries, args.json_output, explanations, args.explain)
        if args.command == "scan":
            scan = scan_line(args.line)
            if args.json_output:
                print(json.dumps({"schema_version": SCHEMA_VERSION, **scan}, ensure_ascii=False, indent=2))
            else:
                print(format_scan(scan, concise=args.format == "concise"))
            return 0
        if args.command != "lookup":
            _parser().print_help()
            return 2
        query = " ".join(args.terms)
        allow_inflection = not args.exact
        allow_fuzzy = not args.no_fuzzy and not args.exact
        allow_fallback = not args.no_fallback and not args.curated_only
        entries = lookup(query, allow_inflection=allow_inflection, allow_fuzzy=allow_fuzzy, allow_fallback=allow_fallback, include_overlay=not args.curated_only)
        _record_default_lookup_miss(query, entries, args)
        explanations = explain_lookup(query, allow_inflection=allow_inflection, allow_fuzzy=allow_fuzzy, allow_fallback=allow_fallback, include_overlay=not args.curated_only) if args.json_output or args.explain else None
        return _show(entries, args.json_output, explanations, args.explain)
    except (QueryError, EcdictError, SdcvError) as error:
        print(f"輸入不符合範圍：{error}", file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("已取消；未寫入任何資料。", file=sys.stderr)
        return 130

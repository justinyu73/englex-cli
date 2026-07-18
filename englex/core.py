"""Lookup, validation, and presentation rules for englex."""

import re

from .data import seed_entries, user_entries
from .ecdict import lookup_entry as ecdict_lookup_entry


class QueryError(ValueError):
    """Raised for input that is outside englex's term-oriented scope."""


def normalize(text):
    return " ".join(text.casefold().split())


def validate_query(text):
    """Accept a short engineering term, never prose or multi-line input."""
    if not isinstance(text, str) or not text.strip():
        raise QueryError("請輸入一個術語。")
    if "\n" in text or "\r" in text:
        raise QueryError("只接受單行術語，不接受換行文字。")
    compact = " ".join(text.split())
    if len(compact) > 80:
        raise QueryError("術語最長為 80 個字元。")
    if len(compact.split()) > 5:
        raise QueryError("只接受 1–5 個詞的術語；不接受句子或段落。")
    if re.search(r"[.!?。！？]", compact):
        raise QueryError("只接受術語；請勿輸入句子或段落。")
    return compact


def validate_scan_text(text):
    """Accept one explicit selection line without treating it as a term query."""
    if not isinstance(text, str) or not text.strip():
        raise QueryError("請輸入一行選取文字。")
    if "\n" in text or "\r" in text:
        raise QueryError("scan 只接受一行選取文字。")
    if len(text) > 200:
        raise QueryError("scan 最長為 200 個字元。")
    return text


def _inflection_candidates(needle):
    """Return bounded, deterministic single-word base-form candidates."""
    if len(needle.split()) != 1:
        return []
    candidates = []

    def add(value):
        if len(value) >= 2 and value != needle and value not in candidates:
            candidates.append(value)

    if needle.endswith("ies") and len(needle) > 3:
        add(needle[:-3] + "y")
    if needle.endswith("ing") and len(needle) > 4:
        stem = needle[:-3]
        add(stem)
        add(stem + "e")
        if len(stem) >= 2 and stem[-1] == stem[-2]:
            add(stem[:-1])
    if needle.endswith("ed") and len(needle) > 3:
        stem = needle[:-2]
        add(stem)
        add(stem + "e")
        if len(stem) >= 2 and stem[-1] == stem[-2]:
            add(stem[:-1])
    if needle.endswith("es") and len(needle) > 3:
        add(needle[:-2])
        add(needle[:-1])
    if needle.endswith("s") and len(needle) > 2:
        add(needle[:-1])
    return candidates


def _within_one_edit(left, right):
    """Return true only for a deterministic Levenshtein distance of one or less."""
    if abs(len(left) - len(right)) > 1:
        return False
    if left == right:
        return True
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right)) == 1
    shorter, longer = (left, right) if len(left) < len(right) else (right, left)
    index = longer_index = differences = 0
    while index < len(shorter) and longer_index < len(longer):
        if shorter[index] == longer[longer_index]:
            index += 1
            longer_index += 1
        else:
            differences += 1
            longer_index += 1
            if differences > 1:
                return False
    return True


def _is_fuzzy_candidate(needle, candidate):
    return len(needle.split()) == len(candidate.split()) == 1 and _within_one_edit(needle, candidate)


def _ranked_matches(query, include_prefix=False, allow_inflection=True, allow_fuzzy=True, include_overlay=True):
    """Rank local entries: exact, bounded inflection, bounded fuzzy, then prefixes."""
    needle = normalize(validate_query(query))
    inflections = _inflection_candidates(needle) if allow_inflection else []
    ranked = []
    sources = [("user_overlay", user_entries()), ("shipped", seed_entries())] if include_overlay else [("shipped", seed_entries())]
    for source_name, entries in sources:
        for entry in entries:
            canonical = normalize(entry["term"])
            aliases = [normalize(alias) for alias in entry.get("aliases", [])]
            if canonical == needle:
                rank = 0 if source_name == "user_overlay" else 1
                match = f"{source_name}_canonical_exact"
            elif needle in aliases:
                rank = 2 if source_name == "user_overlay" else 3
                match = f"{source_name}_alias_exact"
            elif canonical in inflections:
                rank = 4 if source_name == "user_overlay" else 5
                match = f"{source_name}_canonical_inflection"
            elif any(alias in inflections for alias in aliases):
                rank = 6 if source_name == "user_overlay" else 7
                match = f"{source_name}_alias_inflection"
            elif allow_fuzzy and not include_prefix and _is_fuzzy_candidate(needle, canonical):
                rank = 8 if source_name == "user_overlay" else 9
                match = f"{source_name}_canonical_fuzzy"
            elif allow_fuzzy and not include_prefix and any(_is_fuzzy_candidate(needle, alias) for alias in aliases):
                rank = 10 if source_name == "user_overlay" else 11
                match = f"{source_name}_alias_fuzzy"
            elif include_prefix and canonical.startswith(needle):
                rank = 12 if source_name == "user_overlay" else 13
                match = f"{source_name}_canonical_prefix"
            elif include_prefix and any(alias.startswith(needle) for alias in aliases):
                rank = 14 if source_name == "user_overlay" else 15
                match = f"{source_name}_alias_prefix"
            else:
                continue
            ranked.append((rank, canonical, entry, match))
    return sorted(ranked, key=lambda item: (item[0], item[1]))


def _ranked_entries(query, include_prefix=False, allow_inflection=True, allow_fuzzy=True, include_overlay=True):
    return [entry for _, _, entry, _ in _ranked_matches(query, include_prefix, allow_inflection, allow_fuzzy, include_overlay)]


def all_entries():
    """Seed data remains separate; user data is overlaid only in memory."""
    return [*user_entries(), *seed_entries()]


def _scan_name_pattern(name):
    """Build a case-insensitive exact-name pattern with token boundaries."""
    normalized = normalize(name)
    pieces = [re.escape(piece) for piece in normalized.split()]
    return re.compile(r"(?<!\w)" + r"\s+".join(pieces) + r"(?!\w)", re.IGNORECASE)


def _scan_candidates():
    """Return only private and curated exact identifiers; never fallback data."""
    candidates = []
    sources = (("private", 0, user_entries()), ("curated", 1, seed_entries()))
    form_priority = {"abbreviation": 0, "canonical": 1, "alias": 2, "abbreviation_full_name": 3}
    for source_layer, source_priority, entries in sources:
        for entry in entries:
            names = [(entry["term"], "canonical")]
            names.extend((alias, "alias") for alias in entry.get("aliases", []))
            abbreviation = entry.get("abbreviation")
            if abbreviation:
                names.extend([
                    (abbreviation["short"], "abbreviation"),
                    (abbreviation["full_name"], "abbreviation_full_name"),
                ])
            for name, match_type in names:
                if not isinstance(name, str) or not name.strip():
                    continue
                candidates.append({
                    "entry": entry,
                    "source_layer": source_layer,
                    "source_priority": source_priority,
                    "match_type": match_type,
                    "form_priority": form_priority[match_type],
                    "pattern": _scan_name_pattern(name),
                })
    return candidates


def _context_ranking(entry, text, start, end):
    """Score multi-sense triggers only against the text outside this match span."""
    senses = entry.get("senses", [])
    if len(senses) <= 1:
        return None
    context_text = text[:start] + (" " * (end - start)) + text[end:]
    scores = []
    for number, sense in enumerate(senses, start=1):
        matched_triggers = [
            trigger for trigger in sense.get("context_triggers", [])
            if _scan_name_pattern(trigger).search(context_text)
        ]
        scores.append({
            "sense_number": number,
            "score": len(matched_triggers),
            "matched_triggers": matched_triggers,
        })
    highest_score = max(score["score"] for score in scores)
    leaders = [score for score in scores if score["score"] == highest_score]
    if highest_score and len(leaders) == 1:
        leader = leaders[0]
        return {
            "decision": "most_likely",
            "most_likely_sense_number": leader["sense_number"],
            "matched_triggers": leader["matched_triggers"],
            "scores": scores,
        }
    return {
        "decision": "undetermined",
        "most_likely_sense_number": None,
        "matched_triggers": [],
        "scores": scores,
    }


def _scan_entry_view(entry, source_layer, context_ranking=None):
    """Return a display-safe entry copy; private provenance never exposes URLs."""
    view = {
        "term": entry["term"],
        "aliases": entry.get("aliases", []),
        "status": entry["status"],
        "trust_level": entry.get("trust_level", "unknown"),
        "senses": entry["senses"],
        "source_layer": source_layer,
        "provenance": provenance_summary(entry),
    }
    if entry.get("abbreviation"):
        view["abbreviation"] = entry["abbreviation"]
    if context_ranking is not None:
        view["context_ranking"] = context_ranking
    return view


def scan_line(text):
    """Find longest, exact, non-overlapping private or curated terms in one line."""
    text = validate_scan_text(text)
    matches = []
    for candidate in _scan_candidates():
        for found in candidate["pattern"].finditer(text):
            matches.append({**candidate, "start": found.start(), "end": found.end(), "text": found.group(0)})
    matches.sort(key=lambda item: (
        -(item["end"] - item["start"]),
        item["source_priority"],
        item["form_priority"],
        item["start"],
        normalize(item["entry"]["term"]),
    ))
    accepted, occupied = [], []
    for match in matches:
        if any(match["start"] < end and start < match["end"] for start, end in occupied):
            continue
        accepted.append(match)
        occupied.append((match["start"], match["end"]))
    accepted.sort(key=lambda item: (item["start"], item["end"], item["source_priority"], item["form_priority"]))
    results = []
    for match in accepted:
        results.append({
            "start": match["start"],
            "end": match["end"],
            "text": match["text"],
            "match_type": match["match_type"],
            "entry": _scan_entry_view(
                match["entry"],
                match["source_layer"],
                _context_ranking(match["entry"], text, match["start"], match["end"]),
            ),
        })
    unmatched = []
    for token in re.finditer(r"[A-Za-z0-9][A-Za-z0-9'_/-]*", text):
        if not any(token.start() < result["end"] and result["start"] < token.end() for result in results):
            unmatched.append({
                "start": token.start(),
                "end": token.end(),
                "text": token.group(0),
                "private_add": {"command": "private add", "term": token.group(0)},
            })
    return {"input": text, "results": results, "unmatched": unmatched}


def format_scan(scan, concise=False):
    """Render deterministic human output for the same scan object used by JSON."""
    if not scan["results"]:
        return "找不到已知工程術語。"
    lines = []
    for result in scan["results"]:
        entry = result["entry"]
        span = f"{result['start']}:{result['end']}"
        context_ranking = entry.get("context_ranking")
        if concise:
            context_label = ""
            if context_ranking:
                context_label = (
                    f"／最可能義項：{context_ranking['most_likely_sense_number']}"
                    if context_ranking["decision"] == "most_likely"
                    else "／上下文：無法判定"
                )
            lines.append(f"{span} {result['text']} → {entry['term']} [{result['match_type']}／{entry['source_layer']}／信任：{entry['trust_level']}{context_label}]")
            continue
        card = [
            f"範圍：{span}；命中：{result['text']}；類型：{result['match_type']}",
            entry["term"],
            f"狀態：{entry['status']}",
            f"信任等級：{trust_level_summary(entry)}",
            f"別名：{', '.join(entry['aliases']) or '—'}",
            f"來源紀錄：{entry['provenance']['message']}",
            f"資料層：{entry['source_layer']}",
        ]
        if context_ranking:
            if context_ranking["decision"] == "most_likely":
                card.append(
                    f"最可能義項：{context_ranking['most_likely_sense_number']}"
                    f"（命中線索：{', '.join(context_ranking['matched_triggers'])}）"
                )
            else:
                card.append("上下文判定：無法由上下文判定")
        if len(entry["senses"]) == 1:
            sense = entry["senses"][0]
            card.extend([f"領域：{sense['domain']}", f"釋義：{sense['definition']}"])
        else:
            card.append("可能義項：")
            for number, sense in enumerate(entry["senses"], start=1):
                marker = "最可能；" if context_ranking and context_ranking["decision"] == "most_likely" and context_ranking["most_likely_sense_number"] == number else ""
                card.append(f"{number}. {marker}[{sense['domain']}] {sense['definition']}")
                if sense.get("context_triggers"):
                    card.append(f"   線索：{', '.join(sense['context_triggers'])}")
        if any(sense.get("context_required") for sense in entry["senses"]):
            card.append("注意：需要上下文；請依所在產品、團隊或技術文件確認。")
        lines.append("\n".join(card))
        abbreviation = entry.get("abbreviation")
        if abbreviation:
            lines.append(f"縮寫：{abbreviation['short']}＝{abbreviation['full_name']}（{abbreviation['kind']}）")
    if scan["unmatched"]:
        lines.append("未命中：" + ", ".join(item["text"] for item in scan["unmatched"]))
        lines.append("明示新增 private：" + "; ".join(
            f"englex private add --term {item['private_add']['term']}" for item in scan["unmatched"]
        ))
    return "\n\n".join(lines)


def provenance_summary(entry):
    """Return an offline, safe-to-display summary without making correctness claims."""
    provenance = entry.get("provenance", {})
    kind = provenance.get("kind")
    if kind == "legacy":
        return {"kind": kind, "message": "legacy；未追溯驗證"}
    if kind == "private":
        return {"kind": kind, "message": "private；僅本機資料"}
    if kind == "sourced":
        return {"kind": kind, "message": "sourced；來源紀錄，不等同正確性", "source_url": provenance["source_url"]}
    if kind == "no_public_source":
        return {"kind": kind, "message": "no_public_source；來源紀錄，不等同正確性", "reason": provenance["reason"]}
    if kind == "local_external":
        return {"kind": kind, "message": "local_external；使用者明示的本機資料，Englex 未驗證正確性或授權"}
    return {"kind": "unknown", "message": "provenance 狀態無法判讀"}


def trust_level_summary(entry):
    """Return the visible, upgradeable review label without inferring correctness."""
    labels = {
        "maintainer_verified": "maintainer_verified（維護者／專家審定）",
        "community": "community（社群提供或修訂，未經維護者審定）",
        "ai_drafted": "ai_drafted（AI 草擬，未經人工審定）",
        "legacy": "legacy（既有隨附，未回溯驗證）",
    }
    return labels.get(entry.get("trust_level"), "unknown（信任等級無法判讀）")


def explain_lookup(query, include_prefix=False, allow_inflection=True, allow_fuzzy=True, allow_fallback=True, include_overlay=True):
    """Explain deterministic match order and visible provenance for local results."""
    explanations = []
    matches = _ranked_matches(query, include_prefix, allow_inflection, allow_fuzzy, include_overlay)
    for position, (_, _, entry, match) in enumerate(matches, start=1):
        explanations.append({"term": entry["term"], "rank": position, "match": match, "provenance": provenance_summary(entry)})
    if not explanations and allow_fallback and not include_prefix:
        fallback = ecdict_lookup_entry(normalize(validate_query(query)))
        if fallback:
            explanations.append({"term": fallback["term"], "rank": 1, "match": "ecdict_generic_fallback", "provenance": provenance_summary(fallback)})
    return explanations


def lookup(query, entries=None, allow_inflection=True, allow_fuzzy=True, allow_fallback=True, include_overlay=True):
    if entries is None:
        results = _ranked_entries(query, allow_inflection=allow_inflection, allow_fuzzy=allow_fuzzy, include_overlay=include_overlay)
        if results or not allow_fallback:
            return results
        fallback = ecdict_lookup_entry(normalize(validate_query(query)))
        return [fallback] if fallback else []
    needle = normalize(validate_query(query))
    haystack = entries
    matches = []
    for entry in haystack:
        names = [entry["term"], *entry.get("aliases", [])]
        if any(normalize(name) == needle for name in names):
            matches.append(entry)
    return matches


def find(prefix, entries=None):
    if entries is None:
        return _ranked_entries(prefix, include_prefix=True, allow_inflection=False)
    prefix = validate_query(prefix)
    if len(prefix.split()) != 1:
        raise QueryError("prefix 搜尋只接受一個詞。")
    needle = normalize(prefix)
    haystack = all_entries() if entries is None else entries
    matches = []
    for entry in haystack:
        names = [entry["term"], *entry.get("aliases", [])]
        if any(normalize(name).startswith(needle) for name in names):
            matches.append(entry)
    return sorted(matches, key=lambda item: normalize(item["term"]))


def format_card(entry):
    """Render a compact, non-persistent terminal card."""
    aliases = ", ".join(entry.get("aliases", [])) or "—"
    senses = entry["senses"]
    lines = [
        entry["term"],
        f"狀態：{entry['status']}",
        f"信任等級：{trust_level_summary(entry)}",
        f"別名：{aliases}",
        f"來源紀錄：{provenance_summary(entry)['message']}",
    ]
    if entry.get("source_layer"):
        lines.append(f"資料層：{entry['source_layer']}")
    if len(senses) == 1:
        sense = senses[0]
        lines.extend([f"領域：{sense['domain']}", f"釋義：{sense['definition']}"])
    else:
        lines.append("可能義項：")
        for number, sense in enumerate(senses, start=1):
            lines.append(f"{number}. [{sense['domain']}] {sense['definition']}")
            if sense.get("context_triggers"):
                lines.append(f"   線索：{', '.join(sense['context_triggers'])}")
    if any(sense.get("context_required") for sense in senses):
        lines.append("注意：需要上下文；請依所在產品、團隊或技術文件確認。")
    urls = [sense["source_url"] for sense in senses if sense.get("source_url")]
    if urls:
        lines.append(f"來源：{', '.join(urls)}")
    return "\n".join(lines)

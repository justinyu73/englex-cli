"""Local data loading and private overlay persistence."""

import json
import os
import re
from importlib import resources
from pathlib import Path


SCHEMA_VERSION = 2
PROVENANCE_VERSION = 1
TRUST_LEVELS = frozenset({"maintainer_verified", "community", "ai_drafted", "legacy"})
HTTPS_URL = re.compile(r"^https://[A-Za-z0-9][A-Za-z0-9.-]*(?::[0-9]{1,5})?(?:[/?#][^\s]*)?$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
GRANDFATHERED_TRUST_TERMS = frozenset({
    "sdcv", "backpressure", "feature flag", "circuit breaker", "eventual consistency",
    "vector database", "prompt", "agent memory", "autonomous agent", "token window",
    "AI hallucination", "orchestration",
})


def _seed_payload():
    content = resources.files("englex").joinpath("seed_data.json").read_text(encoding="utf-8")
    return json.loads(content)


def _normalize_entry(entry, default_provenance, default_trust_level=None):
    """Add in-memory defaults without rewriting seed or historical overlays."""
    normalized = dict(entry)
    if "senses" not in normalized:
        normalized.update({
            "schema_version": SCHEMA_VERSION,
            "term": entry.get("term", ""),
            "aliases": entry.get("aliases", []),
            "status": entry.get("status", "使用者詞條"),
            "shareable": entry.get("shareable", False),
            "senses": [{
            "domain": entry.get("domain", "未分類"),
            "definition": entry.get("definition", ""),
            }],
        })
    normalized.setdefault("provenance", default_provenance)
    if default_trust_level is not None:
        normalized.setdefault("trust_level", default_trust_level)
    return normalized


def seed_entries():
    """Return bundled schema-v2 entries without writing package data."""
    payload = _seed_payload()
    legacy = {"version": PROVENANCE_VERSION, "kind": "legacy"}
    legacy_terms = set(payload.get("legacy_terms", []))
    return [_normalize_entry(entry, legacy if entry.get("term") in legacy_terms else {}) for entry in payload["entries"]]


def overlay_path():
    """Return the user-private overlay location without creating it."""
    data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(data_home) if data_home else Path.home() / ".local" / "share"
    return base / "englex" / "overlay.json"


def wishlist_path():
    """Return the opt-in local miss-wishlist location without creating it."""
    return overlay_path().with_name("wishlist.json")


def _wishlist_payload():
    """Read only the bounded local wishlist shape; malformed data fails closed."""
    path = wishlist_path()
    if not path.exists():
        return {"enabled": False, "terms": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"enabled": False, "terms": []}
    if (
        not isinstance(payload, dict)
        or set(payload) != {"enabled", "terms"}
        or not isinstance(payload["enabled"], bool)
        or not isinstance(payload["terms"], list)
        or any(not isinstance(term, str) or not term.strip() for term in payload["terms"])
    ):
        return {"enabled": False, "terms": []}
    return {"enabled": payload["enabled"], "terms": payload["terms"]}


def _save_wishlist(payload):
    """Persist only the opt-in wishlist state and miss terms."""
    path = wishlist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def wishlist_enabled():
    """Return whether the user explicitly enabled local miss recording."""
    return _wishlist_payload()["enabled"]


def set_wishlist_enabled(enabled):
    """Explicitly toggle miss recording without changing existing wishlist terms."""
    payload = _wishlist_payload()
    payload["enabled"] = bool(enabled)
    _save_wishlist(payload)


def wishlist_terms():
    """Return only the local wishlist terms, never query context or history."""
    return list(_wishlist_payload()["terms"])


def record_wishlist_term(term, require_enabled=True):
    """Record one term through the single local wishlist persistence path."""
    payload = _wishlist_payload()
    if require_enabled and not payload["enabled"]:
        return False
    normalized = " ".join(term.casefold().split())
    if normalized in {" ".join(item.casefold().split()) for item in payload["terms"]}:
        return False
    payload["terms"].append(term)
    _save_wishlist(payload)
    return True


def record_wishlist_miss(term):
    """Record one normalized lookup miss only after explicit opt-in."""
    return record_wishlist_term(term, require_enabled=True)


def clear_wishlist():
    """Clear local wishlist terms while preserving the user's opt-in setting."""
    path = wishlist_path()
    if not path.exists():
        return False
    payload = _wishlist_payload()
    if not payload["terms"]:
        return False
    payload["terms"] = []
    _save_wishlist(payload)
    return True


def raw_user_entries():
    """Read the user overlay without migration or persistence."""
    path = overlay_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def user_entries():
    """Return private user entries with in-memory provenance defaults only."""
    private = {"version": PROVENANCE_VERSION, "kind": "private"}
    return [_normalize_entry(entry, private, default_trust_level="community") for entry in raw_user_entries()]


def save_user_entries(entries):
    """Persist only the private user overlay."""
    path = overlay_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def local_source_layers():
    """Return safe local-layer availability without reading private entry content."""
    from .ecdict import baseline_path, validate_store

    ecdict_path = baseline_path()
    ecdict_errors = validate_store() if ecdict_path.is_file() else []
    return {
        "schema_version": SCHEMA_VERSION,
        "layers": [
            {"id": "private_overlay", "state": "available" if overlay_path().is_file() else "not_installed"},
            {"id": "englex_curated", "state": "available"},
            {"id": "ecdict_fallback", "state": "invalid" if ecdict_errors else ("available" if ecdict_path.is_file() else "not_installed")},
            {"id": "sdcv", "state": "explicit_only"},
        ],
    }


def _validate_provenance(provenance, location, allow_legacy, allow_private):
    if not isinstance(provenance, dict) or provenance.get("version") != PROVENANCE_VERSION:
        return [f"{location}: invalid provenance"]
    kind = provenance.get("kind")
    if kind == "legacy":
        return [] if allow_legacy and set(provenance) == {"version", "kind"} else [f"{location}: legacy provenance is not allowed"]
    if kind == "private":
        return [] if allow_private and set(provenance) == {"version", "kind"} else [f"{location}: private provenance is not allowed"]
    if kind == "sourced":
        if set(provenance) != {"version", "kind", "source_url"} or not isinstance(provenance.get("source_url"), str) or not HTTPS_URL.fullmatch(provenance["source_url"]):
            return [f"{location}: sourced provenance requires a valid HTTPS source_url"]
        return []
    if kind == "no_public_source":
        if set(provenance) != {"version", "kind", "reason"} or not isinstance(provenance.get("reason"), str) or not provenance["reason"].strip():
            return [f"{location}: no_public_source provenance requires a reason"]
        return []
    return [f"{location}: invalid provenance kind"]


def _validate_abbreviation(abbreviation, location):
    """Validate the optional, local structured abbreviation contract."""
    if abbreviation is None:
        return []
    required = {"short", "full_name", "display_name", "kind"}
    # Legacy records may still carry the retired context_required flag; it is
    # tolerated when boolean but never required and no longer written.
    allowed = required | {"context_required"}
    if not isinstance(abbreviation, dict) or not required <= set(abbreviation) <= allowed:
        return [f"{location}: invalid abbreviation record"]
    errors = []
    for field in ("short", "full_name", "display_name", "kind"):
        value = abbreviation.get(field)
        if not isinstance(value, str) or not value.strip() or "\n" in value or "\r" in value:
            errors.append(f"{location}: invalid abbreviation {field}")
    if "context_required" in abbreviation and not isinstance(abbreviation["context_required"], bool):
        errors.append(f"{location}: abbreviation context_required must be boolean")
    return errors


def _validate_attribution(entry, location, source):
    """Require review evidence for new public trust upgrades, not private overlays."""
    if entry.get("trust_level") not in {"community", "maintainer_verified"}:
        return []
    if entry.get("provenance", {}).get("kind") == "private":
        return []

    attribution = entry.get("attribution")
    if not isinstance(attribution, dict):
        return [f"{location}: trust upgrade requires attribution"]
    if attribution.get("kind") == "grandfathered":
        expected = {"kind": "grandfathered", "note": "原始 seed,無正式升級紀錄"}
        if source != "seed" or entry.get("term") not in GRANDFATHERED_TRUST_TERMS or attribution != expected:
            return [f"{location}: invalid grandfathered attribution"]
        return []

    required = {"kind", "upgraded_by", "evidence", "date"}
    if set(attribution) != required or attribution.get("kind") != "upgrade":
        return [f"{location}: invalid trust-upgrade attribution"]
    for field in ("upgraded_by", "evidence"):
        value = attribution.get(field)
        if not isinstance(value, str) or not value.strip() or "\n" in value or "\r" in value:
            return [f"{location}: invalid trust-upgrade attribution {field}"]
    if not isinstance(attribution.get("date"), str) or not ISO_DATE.fullmatch(attribution["date"]):
        return [f"{location}: invalid trust-upgrade attribution date"]
    return []


def validate_entries(entries, source="data", allow_legacy=False, allow_private=False):
    """Return deterministic schema-v2 validation errors for one data source."""
    errors, labels = [], {}
    for index, entry in enumerate(entries):
        location = f"{source}[{index}]"
        if entry.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"{location}: invalid schema_version")
        errors.extend(_validate_provenance(entry.get("provenance"), location, allow_legacy, allow_private))
        if entry.get("trust_level") not in TRUST_LEVELS:
            errors.append(f"{location}: invalid trust_level")
        errors.extend(_validate_attribution(entry, location, source))
        errors.extend(_validate_abbreviation(entry.get("abbreviation"), location))
        for field in ("term", "status", "senses"):
            if not entry.get(field):
                errors.append(f"{location}: empty required field {field}")
        if not isinstance(entry.get("aliases"), list):
            errors.append(f"{location}: aliases must be a list")
        term = entry.get("term", "")
        names = [term, *entry.get("aliases", [])] if isinstance(entry.get("aliases"), list) else [term]
        abbreviation = entry.get("abbreviation")
        if isinstance(abbreviation, dict):
            names.extend([abbreviation.get("short"), abbreviation.get("full_name")])
        local_names = set()
        for name in names:
            key = " ".join(str(name).casefold().split())
            if not key or key in local_names:
                continue
            local_names.add(key)
            if key in labels:
                errors.append(f"{location}: duplicate canonical term or alias {name!r}")
            else:
                labels[key] = location
        senses = entry.get("senses", [])
        if not isinstance(senses, list):
            errors.append(f"{location}: senses must be a list")
            continue
        for sense_index, sense in enumerate(senses):
            sense_location = f"{location}.senses[{sense_index}]"
            # Retired context_triggers/context_required keys are ignored when present.
            for field in ("domain", "definition"):
                if field not in sense or sense[field] in ("", None):
                    errors.append(f"{sense_location}: empty required field {field}")
    return errors


def validate_local_data():
    """Validate seed and overlay independently so an overlay can override a seed term."""
    payload = _seed_payload()
    errors = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("seed: invalid schema_version")
    if payload.get("provenance_version") != PROVENANCE_VERSION or payload.get("seed_provenance") != "legacy":
        errors.append("seed: invalid legacy provenance declaration")
    legacy_terms = payload.get("legacy_terms")
    if not isinstance(legacy_terms, list):
        errors.append("seed: legacy_terms must be a list")
    elif set(legacy_terms) != {entry.get("term") for entry in payload.get("entries", []) if "provenance" not in entry}:
        errors.append("seed: legacy_terms must cover exactly the legacy entries")
    errors.extend(validate_entries(seed_entries(), "seed", allow_legacy=True))
    errors.extend(validate_entries(user_entries(), "overlay", allow_private=True))
    from .ecdict import validate_store
    errors.extend(validate_store())
    return errors

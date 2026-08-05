"""Explicit local ECDICT baseline import and lookup; no network access."""

import csv
import hashlib
import os
import sqlite3
import tempfile
from pathlib import Path


SOURCE_URL = "https://github.com/skywind3000/ecdict"
SOURCE_REF = "bc015ed2e24a7abef49fc6dbbb7fe32c1dadaf8b"
STORE_SCHEMA_VERSION = "1"


class EcdictError(ValueError):
    """Raised when an explicit local ECDICT import cannot be completed."""


def baseline_path():
    data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(data_home) if data_home else Path.home() / ".local" / "share"
    return base / "englex" / "ecdict.sqlite"


def _digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return "sha256:" + hasher.hexdigest()


def import_csv(source_path):
    """Build a private SQLite baseline from a caller-selected ECDICT CSV file."""
    source = Path(source_path)
    if not source.is_file():
        raise EcdictError("找不到 ECDICT CSV 檔案。")
    target = baseline_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = _digest(source)
    descriptor, temporary_name = tempfile.mkstemp(prefix="ecdict-", suffix=".sqlite", dir=target.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    count = 0
    try:
        with source.open("r", encoding="utf-8", newline="") as source_handle, sqlite3.connect(temporary) as database:
            reader = csv.DictReader(source_handle)
            if not reader.fieldnames or not {"word", "translation"}.issubset(reader.fieldnames):
                raise EcdictError("ECDICT CSV 必須包含 word 與 translation 欄位。")
            database.executescript(
                """
                CREATE TABLE entries (
                    word TEXT PRIMARY KEY COLLATE NOCASE,
                    phonetic TEXT NOT NULL,
                    translation TEXT NOT NULL,
                    pos TEXT NOT NULL
                );
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                """
            )
            rows = []
            for row in reader:
                word = (row.get("word") or "").strip()
                translation = (row.get("translation") or "").strip()
                if not word or not translation:
                    continue
                rows.append((word, (row.get("phonetic") or "").strip(), translation, (row.get("pos") or "").strip()))
                if len(rows) >= 1000:
                    database.executemany("INSERT OR IGNORE INTO entries VALUES (?, ?, ?, ?)", rows)
                    count += len(rows)
                    rows = []
            if rows:
                database.executemany("INSERT OR IGNORE INTO entries VALUES (?, ?, ?, ?)", rows)
                count += len(rows)
            if not count:
                raise EcdictError("ECDICT CSV 沒有可用的英中詞條。")
            database.executemany(
                "INSERT INTO metadata VALUES (?, ?)",
                [
                    ("schema_version", STORE_SCHEMA_VERSION),
                    ("source_url", SOURCE_URL),
                    ("source_ref", SOURCE_REF),
                    ("source_digest", digest),
                    ("entry_count", str(count)),
                ],
            )
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
        return count
    except (OSError, csv.Error, sqlite3.Error) as error:
        raise EcdictError(f"無法匯入 ECDICT CSV：{error}") from error
    finally:
        if temporary.exists():
            temporary.unlink()


def lookup_entry(query):
    """Return one generic fallback entry only when a local baseline is installed."""
    target = baseline_path()
    if not target.is_file():
        return None
    try:
        with sqlite3.connect(f"file:{target}?mode=ro", uri=True) as database:
            row = database.execute(
                "SELECT word, phonetic, translation, pos FROM entries WHERE word = ? COLLATE NOCASE",
                (query,),
            ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    word, phonetic, translation, pos = row
    detail = translation if not phonetic else f"{translation}\n音標：{phonetic}"
    if pos:
        detail += f"\n詞性：{pos}"
    return {
        "schema_version": 2,
        "term": word,
        "aliases": [],
        "status": "一般詞典 fallback",
        "senses": [{
            "domain": "一般英中詞典",
            "definition": detail,
        }],
        "provenance": {"version": 1, "kind": "sourced", "source_url": SOURCE_URL},
        "trust_level": "community",
        "source_layer": "ECDICT 一般詞典 fallback",
    }


def validate_store():
    """Return local-baseline integrity errors without creating or changing a store."""
    target = baseline_path()
    if not target.exists():
        return []
    try:
        with sqlite3.connect(f"file:{target}?mode=ro", uri=True) as database:
            metadata = dict(database.execute("SELECT key, value FROM metadata"))
            columns = {row[1] for row in database.execute("PRAGMA table_info(entries)")}
    except sqlite3.Error as error:
        return [f"ecdict: 無法讀取本機基底：{error}"]
    if metadata.get("schema_version") != STORE_SCHEMA_VERSION:
        return ["ecdict: 不支援的本機基底版本"]
    if metadata.get("source_url") != SOURCE_URL or metadata.get("source_ref") != SOURCE_REF:
        return ["ecdict: 本機基底來源不符合已鎖定的 ECDICT 版本"]
    if {"word", "phonetic", "translation", "pos"} - columns:
        return ["ecdict: 本機基底缺少必要欄位"]
    return []

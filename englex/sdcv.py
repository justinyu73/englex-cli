"""Explicit, history-disabled adapter for a caller-selected local sdcv dictionary."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .core import validate_query
from .data import PROVENANCE_VERSION, SCHEMA_VERSION


class SdcvError(ValueError):
    """Raised when the explicitly requested local sdcv adapter cannot run."""


def _entry(result):
    if not isinstance(result, dict) or not isinstance(result.get("word"), str) or not isinstance(result.get("definition"), str):
        raise SdcvError("sdcv 回傳格式不完整。")
    definition = result["definition"].strip()
    if not definition:
        raise SdcvError("sdcv 回傳空白釋義。")
    return {
        "schema_version": SCHEMA_VERSION,
        "term": result["word"],
        "aliases": [],
        "status": "外部本機詞典",
        "shareable": False,
        "source_layer": "sdcv 明示本機 StarDict",
        "provenance": {"version": PROVENANCE_VERSION, "kind": "local_external"},
        "trust_level": "community",
        "senses": [{
            "domain": "使用者指定的本機 StarDict",
            "definition": definition,
            "context_triggers": [],
            "context_required": False,
        }],
    }


def lookup(query, data_dir):
    """Query only ``data_dir/dic`` through an installed sdcv executable.

    This is deliberately separate from Englex's ranked lookup. The process gets
    a disposable HOME and no inherited environment, so it cannot write sdcv
    history into the user's account.
    """
    query = validate_query(query)
    data_path = Path(data_dir).expanduser()
    if not data_path.is_dir() or not (data_path / "dic").is_dir():
        raise SdcvError("資料目錄必須存在，且包含 dic/ 子目錄。")
    executable = shutil.which("sdcv")
    if not executable:
        raise SdcvError("找不到 sdcv；請先在本機安裝，或不要使用 lookup-sdcv。")
    with tempfile.TemporaryDirectory(prefix="englex-sdcv-") as isolated_home:
        environment = {
            "HOME": isolated_home,
            "LC_ALL": "C.UTF-8",
            "PATH": os.defpath,
            "SDCV_HISTSIZE": "0",
        }
        result = subprocess.run(
            [executable, "--non-interactive", "--json-output", "--exact-search", "--only-data-dir", "--data-dir", str(data_path), "--", query],
            check=False,
            capture_output=True,
            env=environment,
            text=True,
            timeout=5,
        )
    if result.returncode:
        message = result.stderr.strip() or "sdcv 執行失敗。"
        raise SdcvError(message)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise SdcvError("sdcv 未回傳 JSON 結果。") from error
    if not isinstance(payload, list):
        raise SdcvError("sdcv 回傳格式不支援。")
    return [_entry(item) for item in payload]

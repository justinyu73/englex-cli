#!/usr/bin/env sh
set -eu

artifact_root="$(mktemp -d)"
tool_root="$(mktemp -d)"
source_root="$(mktemp -d)"
install_root="$(mktemp -d)"
run_root="$(mktemp -d)"
trap 'rm -rf "$artifact_root" "$tool_root" "$source_root" "$install_root" "$run_root"' EXIT

grep -F 'pipx install /path/to/englex-*.whl' README.md >/dev/null
grep -F 'python3 -m venv "$HOME/.local/share/englex/venv"' README.md >/dev/null
grep -F 'englex scan "Use canary deployment with SLO and sdcv"' README.md >/dev/null
grep -F 'data.gov.tw/dataset/15275' README.md >/dev/null
test -f CONTRIBUTING.md

python3 - <<'PY'
from pathlib import Path

from englex.data import TRUST_LEVELS

readme = Path("README.md").read_text(encoding="utf-8")
contributing = Path("CONTRIBUTING.md").read_text(encoding="utf-8")
for level in TRUST_LEVELS:
    if f"`{level}`" not in readme:
        raise SystemExit(f"README missing trust level {level}")
    if f"`{level}`" not in contributing:
        raise SystemExit(f"CONTRIBUTING missing trust level {level}")
if '"kind": "upgrade"' not in contributing or '"date": "YYYY-MM-DD"' not in contributing:
    raise SystemExit("CONTRIBUTING does not document the trust-upgrade attribution schema")
PY

mkdir "$source_root/englex"
cp LICENSE README.md pyproject.toml "$source_root"
cp -R englex/. "$source_root/englex"

python3 -m venv "$tool_root"
(
  cd "$run_root"
  "$tool_root/bin/python" -m pip install --disable-pip-version-check --no-cache-dir build
  "$tool_root/bin/python" -m build --outdir "$artifact_root" "$source_root"
)

wheel="$(find "$artifact_root" -maxdepth 1 -type f -name 'englex-*.whl' -print -quit)"
test -n "$wheel"
python3 -m venv "$install_root"
"$install_root/bin/python" -m pip install --no-deps "$wheel"
(cd "$run_root" && "$install_root/bin/englex" lookup --exact embedding | grep -F '把資料轉成數值向量' >/dev/null)

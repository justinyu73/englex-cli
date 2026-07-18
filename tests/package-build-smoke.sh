#!/usr/bin/env sh
set -eu

artifact_root="$(mktemp -d)"
tool_root="$(mktemp -d)"
source_root="$(mktemp -d)"
venv_root="$(mktemp -d)"
run_root="$(mktemp -d)"
trap 'rm -rf "$artifact_root" "$tool_root" "$source_root" "$venv_root" "$run_root"' EXIT

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
sdist="$(find "$artifact_root" -maxdepth 1 -type f -name 'englex-*.tar.gz' -print -quit)"
test -n "$wheel"
test -n "$sdist"

python3 -m venv "$venv_root"
"$venv_root/bin/python" -m pip install --no-deps "$wheel"
(cd "$run_root" && "$venv_root/bin/englex" --help >/dev/null)

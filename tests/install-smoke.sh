#!/usr/bin/env sh
set -eu

source_root="$(mktemp -d)"
install_root="$(mktemp -d)"
trap 'rm -rf "$source_root" "$install_root"' EXIT
mkdir "$source_root/englex"
cp LICENSE README.md pyproject.toml "$source_root"
cp -R englex/. "$source_root/englex"
PIP_NO_CACHE_DIR=1 PIP_NO_INDEX=1 python3 -m pip install --no-deps --no-build-isolation --target "$install_root" "$source_root"
PYTHONPATH="$install_root" "$install_root/bin/englex" lookup --exact embedding
scan_output="$(PYTHONPATH="$install_root" "$install_root/bin/englex" scan --json "Use canary deployment with SLO and sdcv")"
printf '%s\n' "$scan_output" | grep -F '"term": "canary deployment"' >/dev/null
printf '%s\n' "$scan_output" | grep -F '"full_name": "StarDict Console Version"' >/dev/null

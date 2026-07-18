#!/usr/bin/env sh
set -eu

if ! command -v sdcv >/dev/null 2>&1; then
  echo "sdcv is required for this optional local-engine smoke" >&2
  exit 2
fi

fixture_dir="$(mktemp -d)"
trap 'rm -rf "$fixture_dir"' EXIT
python3 -B tests/create_sdcv_smoke_fixture.py "$fixture_dir"
python3 -B -m englex lookup-sdcv --data-dir "$fixture_dir" zorb
python3 -B -m englex lookup-sdcv --json --data-dir "$fixture_dir" zorb

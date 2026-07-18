#!/usr/bin/env sh
set -eu

data_home="$(mktemp -d)"
trap 'rm -rf "$data_home"' EXIT

printf 'private smoke\n\n測試\n本機 lifecycle smoke\n團隊用語\n\n' |
  XDG_DATA_HOME="$data_home" python3 -B -m englex add
XDG_DATA_HOME="$data_home" python3 -B -m englex private list
XDG_DATA_HOME="$data_home" python3 -B -m englex private remove --yes "private smoke"
XDG_DATA_HOME="$data_home" python3 -B -m englex private list --json

printf '\n測試\nP2 private scan smoke\n團隊用語\n\n' |
  XDG_DATA_HOME="$data_home" python3 -B -m englex private add --term "private scan" --abbreviation PS --full-name "Private Scan"
XDG_DATA_HOME="$data_home" python3 -B -m englex scan --json "private scan PS"
if printf '\n測試\nP2 conflict smoke\n團隊用語\n\n' |
  XDG_DATA_HOME="$data_home" python3 -B -m englex private add --term "other private scan" --abbreviation PS --full-name "Private Scan"; then
  echo "private add accepted a duplicate abbreviation" >&2
  exit 1
fi
XDG_DATA_HOME="$data_home" python3 -B -m englex private remove --yes "private scan"

if XDG_DATA_HOME="$data_home" python3 -B -m englex private remove --yes "private smoke"; then
  echo "private remove accepted a missing canonical entry" >&2
  exit 1
fi

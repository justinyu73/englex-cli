#!/usr/bin/env sh
set -eu

python3 -B -m englex validate-data
python3 -B -m englex canary
python3 -B -m englex lookup --json --explain embeding
python3 -B -m englex lookup --exact embedding
python3 -B -m englex lookup --exact "feature flag"
python3 -B -m englex scan --json "Use canary deployment with SLO and sdcv"

ecdict_home="$(mktemp -d)"
trap 'rm -rf "$ecdict_home"' EXIT
printf 'word,phonetic,definition,translation,pos\nzorb,zoːb,,虛構的一般詞典詞條,n\n' > "$ecdict_home/ecdict.csv"
XDG_DATA_HOME="$ecdict_home" python3 -B -m englex import-ecdict "$ecdict_home/ecdict.csv"
XDG_DATA_HOME="$ecdict_home" python3 -B -m englex lookup --exact zorb
if XDG_DATA_HOME="$ecdict_home" python3 -B -m englex lookup --exact --no-fallback zorb; then
  echo "--no-fallback accepted an ECDICT result" >&2
  exit 1
fi

if python3 -B -m englex lookup --exact embeding; then
  echo "--exact accepted a fuzzy candidate" >&2
  exit 1
fi

python3 -B -m englex find roll

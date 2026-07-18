# sdcv B3 local-engine source lock

## Scope

sdcv is an optional, caller-invoked reader for a locally selected StarDict directory. It is not an Englex glossary authority, does not enter the normal `lookup` ranking, and does not supply ECDICT or curated data.

## Frozen implementation source

- Repository: `https://github.com/Dushistov/sdcv`
- Commit: `f1cb0172d1806c9a60d3b0bb0a9044ba3ed3670c`
- License: GPL-2.0-only
- Local command contract used by Englex: `--non-interactive --json-output --exact-search --only-data-dir --data-dir PATH -- TERM`

## Local-data and privacy boundary

The user supplies a root directory that contains `dic/`; Englex never downloads, vendors, indexes, or attributes a third-party StarDict dataset. `lookup-sdcv` calls only the installed local executable with a disposable `HOME`, `SDCV_HISTSIZE=0`, an isolated environment, and a five-second timeout. The result is labelled `local_external`; it is neither curated nor a claim that the selected dictionary is correct or licensed for a particular use.

`tests/create_sdcv_smoke_fixture.py` generates an Englex-owned, one-entry Traditional-Chinese fixture solely for local engine acceptance. It is not a product dictionary or an external data source.

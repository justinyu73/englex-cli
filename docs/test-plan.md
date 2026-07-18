# englex v0.6 test plan

## Test approach

Tests use only `unittest` and Python standard-library helpers. Every test sets `XDG_DATA_HOME` to a `TemporaryDirectory`; tests therefore never read or modify the real user overlay.

The [product feature map](product-feature-map.md) separates currently testable MVP behavior from future candidate units; it does not expand this test plan by itself.

## Unit coverage

- Exact lookup returns the intended seed entry.
- Alias lookup resolves `RAG` and `function calling`.
- Case and whitespace normalization resolve `Context WINDOW`.
- Prefix lookup returns the local `roll` entries in deterministic order.
- Single-word plural, `-ed`, and `-ing` queries can resolve only to an existing local term or alias and are labelled as inflection matches.
- A single edit-distance candidate is deterministic, labelled as fuzzy, and can be disabled with `lookup --no-fuzzy`.
- `lookup --exact` retains canonical／alias matches and rejects both inflection and fuzzy candidates.
- Validation rejects overlong, sentence-like, and excessive-token input.
- An unknown term is reported as not found.
- `canary` preserves engineering release/testing meaning rather than a default bird translation.
- Ranking prefers a user canonical match, then a seed canonical match, then aliases.
- `canary` exposes separate release-channel, deployment, and test senses; `capsule` exposes multiple context-required senses.
- Schema validation catches invalid versions, duplicate names, empty fields, and incomplete context-required senses.
- Existing shipped entries validate as legacy provenance; historic overlays remain readable without being rewritten.
- Curated provenance rejects a missing record, non-HTTPS sourced URL, or missing no-public-source reason; valid sourced and no-public-source records pass.
- The curated expansion batch has deterministic local lookup results and syntactically valid sourced provenance records.
- A caller-selected local ECDICT CSV imports into a separate SQLite store; it is used only after private and curated misses, labels its fallback source, and can be disabled with `--no-fallback`.
- `lookup-sdcv --data-dir PATH TERM` requires an explicit StarDict root containing `dic/`, uses exact local-only data, labels results as external local data, and never changes normal lookup ranking.
- `sources --json` reports only stable layer state and does not create or expose a private overlay.
- `lookup --curated-only TERM` returns shipped curated data even when a private overlay has a matching term, and does not use ECDICT.
- The fixed local gen-ai-glossary source expands only selected aliases with deterministic lookup fixtures.
- `private list` exposes private content only after an explicit management command, succeeds with an empty overlay, and `private remove --yes TERM` removes canonical-exact entries without alias matching.
- `scan` accepts only one explicit line of at most 200 characters, then returns longest exact non-overlapping private／curated canonical, alias, or structured-abbreviation matches with stable character spans and unmatched summaries.
- `scan` never uses ECDICT, sdcv, inflection, fuzzy, provider, or network fallbacks; a private exact match wins over a curated match.
- Structured abbreviations require every local schema field; `private add --term TERM` is explicit, preserves conflict rejection, and may add a private structured abbreviation only when short and full name are both supplied.
- The dependency-free VS Code entry statically parses and its local smoke proves it passes only an explicit selected string to the configured local executable's scan contract.
- The checked-in VS Code launch contract pins the extension host to the WSL workspace and prepends the sibling checkout's `.venv/bin`; the adapter smoke rejects a missing or changed WSL launch shape.

## Privacy and data-isolation coverage

- A static guard rejects networking imports everywhere and allows a subprocess import only in the isolated `sdcv` adapter.
- Lookup succeeds without creating a user overlay.
- Export includes only entries whose user-supplied `shareable` flag is true.
- Interactive add is tested with mocked prompts and writes only beneath temporary `XDG_DATA_HOME`; it defaults the entry to private.
- Private lifecycle smoke creates, lists, and removes an entry only beneath a temporary `XDG_DATA_HOME`; a second remove must fail without writing unrelated entries.

## CLI integration coverage

CLI calls are exercised in-process with captured stdout and stderr. A successful lookup returns 0 and prints a card; an unknown lookup returns 1 with stderr only; invalid input returns 2 with stderr only. Interactive cancellation is specified as exit 130 and must not write an entry.

`lookup --json` and `find --json` are checked for a local JSON object containing `schema_version`, `results`, and deterministic explanations. Terminal `--explain` is checked for its match tier. Legacy, private, sourced, and no-public-source summaries remain distinguishable without a network call; private summaries do not expose a source URL. `validate-data` is checked against shipped schema-v2 data and entry-level provenance. All provenance checks are local syntax and field checks only.

## CI／PR acceptance 與實際 smoke

Run these commands in WSL or the VS Code Integrated Terminal:

```bash
python3 -B tests/p1_p5_machine_acceptance.py
python3 -m unittest discover -s tests -v
python3 -m englex canary
python3 -m englex "canary deployment"
python3 -m englex find roll
python3 -m englex capsule
python3 -m englex lookup --json canary
python3 -m englex lookup --json --explain embeding
python3 -m englex lookup --no-fuzzy embeding
python3 -m englex lookup --exact embedding
python3 -m englex scan --json "Use canary deployment with SLO and sdcv"
sh tests/smoke.sh
sh tests/install-smoke.sh
sh tests/private-lifecycle-smoke.sh
node --check vscode-extension/extension.js
node tests/vscode-extension-smoke.js
python3 -m englex validate-data
```

Expected outcomes: the test suite passes; `canary` shows three context-required engineering senses; `canary deployment` returns its rollout definition; `capsule` shows multiple uncertain senses; `find roll` returns `roll forward` and `rollback`; the misspelling `embeding` returns `embedding` with an explainable fuzzy match; `--no-fuzzy embeding` returns exit code 1; `--exact embedding` succeeds while `--exact embeding` returns exit code 1; JSON commands return a schema-versioned object; and data validation succeeds. `sh tests/smoke.sh` runs the essential product behavior end to end. To manually check overlay isolation, use a disposable directory:

`python3 -B tests/p1_p5_machine_acceptance.py` is the P1–P5 machine simulation: it exercises the unit contract, source-checkout scan, temporary-XDG private lifecycle and collision rejection, offline disposable installation whose installed `englex` command scans a known line, and the dependency-free VS Code selection adapter. It is deterministic product evidence, not an external/provider review and not an automatic Git promotion.

這組命令是 MVP acceptance 的唯一證據形式：CI／PR 必須通過，或在目標終端完成等價 smoke。文字審查表不構成 acceptance。

```bash
XDG_DATA_HOME="$(mktemp -d)" python3 -m englex add
```

The resulting overlay, if any, must exist only below that temporary directory.

For B3/B4 actual local-engine acceptance, after installing `sdcv`, run:

```bash
sh tests/sdcv-smoke.sh
```

It creates an Englex-owned one-entry StarDict fixture in a temporary directory and proves the installed engine works through `lookup-sdcv`; it neither fetches nor endorses an external dictionary dataset.

`sh tests/install-smoke.sh` installs only the current local checkout into a disposable directory with `PIP_NO_INDEX=1`, then invokes the resulting `englex` entry point. It must not resolve packages from a network index.

`sh tests/private-lifecycle-smoke.sh` performs the complete local private-overlay lifecycle in a disposable XDG directory. It proves that listing is explicit and removal requires both `--yes` and a canonical exact term; it neither contacts a service nor reads a project file.

For the P5 manual WSL acceptance, first install the checkout into its local virtual environment. After this change is checked out, use VS Code **File → Open Folder** to open the `vscode-extension/` subfolder in a **WSL: Ubuntu** window, then press `F5`. The checked-in `Run Englex Selection (WSL)` configuration opens the Extension Development Host with the sibling `.venv/bin` on `PATH`; the WSL Remote `code` CLI does not support `--extensionDevelopmentPath`. Select `canary deployment` in a new text file and run **Englex: Explain Selected Engineering Terms**. The **Englex Selection** output must show the selected phrase and no command should inspect unselected document text.

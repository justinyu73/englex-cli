# englex v0.6 architecture

## Purpose and environment

englex is a private, offline-first English AI and software-engineering term lookup CLI for a WSL terminal, including the VS Code Integrated Terminal. It is not a general translation product or a background service.

The [product feature map](product-feature-map.md) is the product-scope authority for future work units; this document describes the implemented architecture only.

The boundary excludes browsers, desktop Codex, clipboard input, stdin input, file input, document translation, LLM or Ollama integration, external lookup, cloud sync, telemetry, analytics, and uploads. The sole IDE exception is the dependency-free P5 VS Code command: after the user explicitly selects text and invokes it, the extension passes only that selection to local `englex scan --json`; it does not read a workspace, unselected document content, clipboard, history, or files.

## Lookup flow

```text
user query
  -> term validation
  -> private overlay + shipped schema-v2 curated glossary (in memory)
  -> deterministic canonical, alias, bounded inflection, bounded fuzzy, prefix, or labelled fallback result
  -> optional local ECDICT generic fallback only after no local result
  -> compact terminal term card

lookup --curated-only TERM
  -> shipped schema-v2 curated glossary only; excludes private overlay and ECDICT

lookup-sdcv --data-dir PATH TERM
  -> explicitly selected local StarDict data only; never enters the lookup ranking
  -> compact terminal term card

scan "SELECTED LINE"
  -> explicit one-line selection validation (200 characters maximum)
  -> private + shipped curated canonical, alias, and structured abbreviation identifiers only
  -> longest exact non-overlapping spans, safe provenance summaries, and explicit unmatched/private-add handoffs
  -> stable JSON or concise/expanded terminal output; never ECDICT, sdcv, inflection, fuzzy, provider, or network
```

Validation accepts one to five tokens, at most 80 characters, on one line. It rejects sentence- or paragraph-like queries before lookup. `find` performs local prefix matching only. `lookup` ranks user-overlay canonical exact, shipped canonical exact, aliases, fixed local inflection candidates, single edit-distance candidates, then prefixes; exact matches always win. The edit-distance tier can be disabled with `--no-fuzzy`; `--exact` disables both inflection and fuzzy, retaining canonical／alias matches only. A match returns every listed sense; englex never silently selects an uncertain sense.

## Semantic glossary schema

Schema version 2 stores a canonical `term`, `aliases`, `status`, one or more `senses`, and an entry-level provenance record. Every sense has `domain`, Traditional-Chinese `definition`, `context_triggers`, `context_required`, and optional sense-level `source_url`. The validator rejects duplicate canonical terms or aliases within a source, invalid schema versions, empty required fields, and context-required senses with no context triggers. Legacy v0.1 user overlay records are normalized in memory without rewriting the user's file.

An entry may additionally carry a structured `abbreviation` record with exactly `short`, `full_name`, `display_name`, `kind`, and `context_required`. Both short and full names are exact scan identifiers; the record is not inferred from a tool name. The P1 `sdcv` mapping is one curated record tied to the already locked B3 source, while private abbreviations require the explicit `private add` command.

Entry-level provenance version 1 distinguishes `legacy`, `private`, `sourced`, and `no_public_source`. Existing shipped entries are an explicit legacy manifest; historic user overlays gain private provenance only in memory. Future curated shipped entries must use exactly one of `sourced` with a syntactically valid HTTPS `source_url`, or `no_public_source` with a non-empty reason. `lookup-sdcv` results are transient `local_external` records, not schema-validated curated or overlay data. Validation is syntax-only and never fetches or resolves URLs.

`lookup --json` and `find --json` emit a stable local object with top-level `schema_version`, `results`, and deterministic `explanations`. Each explanation records the local match tier and a safe provenance summary. `lookup` may additionally match a single-word local canonical or alias through fixed plural, `-ed`, or `-ing` base-form candidates, then through a single edit-distance candidate; exact matches always rank first. `find` remains prefix-only. `lookup --no-fuzzy` disables only the edit-distance tier. `--explain` shows the same match tier in terminal output. `legacy` is explicitly labelled unverified, `private` remains local-only, and provenance is never presented as correctness or product acceptance. This is an interface boundary for a possible future local integration, not an implemented UI.

## Data ownership and persistence

The shipped, manually authored seed data is package-owned and read-only at runtime. User-added entries live only in a private local overlay at `$XDG_DATA_HOME/englex/overlay.json`, or `~/.local/share/englex/overlay.json` when `XDG_DATA_HOME` is unset. Lookup combines the two sources only in memory and never writes an overlay. `private list` is the explicit read surface for that overlay; `private remove --yes TERM` changes it only when `TERM` canonical-exactly matches, never through an alias, fuzzy, or prefix match. An optional ECDICT baseline is built only by explicit `import-ecdict CSV_PATH` into a separate `$XDG_DATA_HOME/englex/ecdict.sqlite`; it is consulted only after no private or curated result and is labelled as a general-dictionary fallback. `lookup-sdcv --data-dir PATH TERM` is a separate, explicit command: it uses only `PATH/dic`, cannot affect normal ranking, runs `sdcv` with a disposable home and history disabled, and returns a visibly external local result. Interactive `add` writes the overlay; new entries are private unless the user explicitly enters `yes` for shareability. `export --shareable-only` writes JSON to stdout and includes only explicitly shareable user entries; it does not upload anything.

`scan` never writes an overlay. Its unmatched tokens include only an explicit `private add` handoff; the user must invoke `private add --term TERM` and complete the existing prompts before a private entry (or a private structured abbreviation) is written. That command preserves private conflict rejection.

## Security boundary

Normal Englex commands make no network requests, start no subprocesses, keep no query history, and have no telemetry. `sources` reads only layer existence and ECDICT schema state; it never reads or displays private entry content. The opt-in `lookup-sdcv` command is the one exception: it starts only the installed local `sdcv` executable with a caller-selected local dictionary directory, a disposable `HOME`, no inherited environment, and `SDCV_HISTSIZE=0`. It does not scan or read caller project files, documents, clipboard contents, or stdin; the only package data normal lookup reads is its own seed lexicon. The security boundary does not defend against a compromised WSL host or weak permissions on the user's local overlay.

## CLI exit-code contract

| Situation | Exit code | Output channel |
| --- | ---: | --- |
| Successful lookup, prefix search, add, or export | 0 | result/status on stdout |
| No matching local term | 1 | explanatory message on stderr |
| Invalid query or invalid CLI usage | 2 | validation/parser message on stderr |
| Interactive add cancelled by EOF or Ctrl-C | 130 | cancellation message on stderr |

## Context-aware terms

`canary` has three engineering senses: an early/experimental release channel, a limited-exposure deployment, and an early-warning test or monitor. englex therefore never defaults it to the bird translation and marks the senses as context-required. `capsule` has no single reliable engineering translation: it may be a packaging unit, a portable execution environment, or a product/SDK/protocol name. The terminal card presents every listed sense and its triggers. `gate`, `ratchet`, `rollback`, `roll forward`, `grounding`, and `provenance` likewise retain code, product, or protocol names where a direct translation would obscure the meaning.

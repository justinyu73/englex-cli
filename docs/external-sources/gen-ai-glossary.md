# gen-ai-glossary B2 source lock

## Scope

gen-ai-glossary supplies AI terminology candidates for Englex curation. It does not become a runtime dependency and its English definitions never replace Englex's Traditional-Chinese engineering meanings.

## Frozen source

- Repository: `https://github.com/danielskry/gen-ai-glossary`
- Commit: `beee4ed4f0a81f53a1c367de63740cfcac729ba8`
- License: MIT
- Candidate data: `data/terms.json`

## B2 import rule

Only non-duplicate terms that receive a separate Englex sense, context boundary, and sourced provenance enter the shipped curated layer. The B2 batch adds `vector database`, `prompt`, and `agent memory`; the v0.4 locked-source batch adds `autonomous agent`, `token window`, and `AI hallucination`, and extends the already sourced `prompt` aliases. It does not import source code, dependencies, generated documentation, or a generic runtime adapter.

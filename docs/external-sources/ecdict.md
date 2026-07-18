# ECDICT B1 source lock

## Scope

ECDICT is the optional offline generic English-Chinese fallback base. It is not an Englex curated engineering definition source and it never overrides the private overlay or shipped curated glossary.

## Frozen source

- Repository: `https://github.com/skywind3000/ecdict`
- Commit: `bc015ed2e24a7abef49fc6dbbb7fe32c1dadaf8b`
- License file digest: `sha256:f8552dd246f61a4e064569eae6194a01c6b3d63b03bf27c6ca863593c549ed0f`
- `ecdict.csv` digest: `sha256:1a6947e04785db63613a92e14903cdae7954f7e84860b10e68e5c7cbb3f9c3cf`
- Observed CSV fields used: `word`, `phonetic`, `translation`, `pos`

## Packaging and runtime boundary

Englex does not vendor the 63 MiB source CSV. The user explicitly selects an already obtained local CSV with `import-ecdict`; englex converts it to `$XDG_DATA_HOME/englex/ecdict.sqlite`. Import and lookup are local-only, do not run upstream programs, do not install dependencies, do not retain query history, and do not inspect project files.

## Attribution

The installed fallback reports ECDICT as its source layer and retains the source repository URL in local provenance. The source lock is not a claim that every definition is an Englex engineering translation or a product-acceptance result.

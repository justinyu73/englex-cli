# Curated glossary source provenance policy

## Purpose

This policy governs future curated glossary entries and materially revised curated entries. Each must include a traceable HTTPS public source URL, or an explicit reason that no public source is applicable. A reason may be appropriate when terminology is inherently local, product-specific, or not represented by a suitable public source.

## Current v0.3 boundary

Entry-level provenance version 1 is now validated locally. Existing shipped seed entries are explicitly legacy and this policy does not claim they were retrospectively verified, sourced, or corrected. Future curated entries must use exactly one of `sourced` with a syntactically valid HTTPS `source_url`, or `no_public_source` with a non-empty reason. Private overlay entries use private provenance and are outside curated shipped-entry enforcement.

## What provenance does not establish

Source provenance records where a future curation decision can be traced. It does not by itself establish factual correctness, replace human review, approve a product change, or constitute product acceptance. Those remain separate human responsibilities.

## Source-catalog rule

Each reusable external source is recorded separately under `docs/external-sources/`. A catalog record must state its publisher, dataset or repository URL, license, intended role, and import boundary before it can supply curated candidates. A source record is not an authorization to fetch, vendor, or import its data.

The National Academy for Educational Research (NAER) academic-terminology datasets are a registered candidate source family. Their discipline-specific CSV datasets provide English–Traditional-Chinese terminology pairs and source metadata under Taiwan's Open Government Data License, version 1.0. They may supply candidate canonical terms, Traditional-Chinese labels, discipline labels, and source URLs; they do not supply Englex's engineering explanation, ambiguity decision, context trigger, or final authority status. The detailed boundary and future intake gates are in [the NAER source record](external-sources/naer-academic-terminology.md).

Before any NAER dataset is used, the selected discipline dataset must be frozen locally with its dataset URL, resource URL, retrieval date, license URL, observed columns, SHA-256 digest, and row count. Only that frozen snapshot may be compared with the shipped curated layer. The import is rejected if the dataset identity, license, required English/Traditional-Chinese fields, or snapshot evidence is missing.

## Privacy and offline boundary

Private overlay entries remain local to the user's data directory and are never uploaded. This policy does not authorize external lookup, automatic source import, LLM-generated sources, cloud sync, telemetry, or any network access.

Development-time acquisition of an explicitly approved, frozen source snapshot is separate from runtime: shipped Englex must not fetch NAER or any other source, retain user queries, or create a network cache.

## Migration and validation boundary

Historical overlays are read without rewriting their on-disk JSON; private provenance is supplied only in memory. Validation does not fetch, resolve, or verify URLs. It checks only the declared fields and HTTPS syntax, so provenance remains distinct from correctness, human review, and product acceptance.

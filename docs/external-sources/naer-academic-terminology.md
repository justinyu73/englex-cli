# NAER academic terminology candidate-source specification

## Scope

The National Academy for Educational Research (NAER) publishes discipline-specific academic-terminology datasets through Taiwan's Government Open Data Platform. This source family is a candidate for expanding Englex's Traditional-Chinese engineering terminology coverage. It is not downloaded, vendored, indexed, or queried by the product in this specification.

## Publisher, access, and license

- Publisher: National Academy for Educational Research (NAER), Taiwan.
- Catalog example: `https://data.gov.tw/dataset/15275` (Cross-strait comparison terminology: computing).
- Dataset shape: separate CSV resources by discipline; the computing catalog lists English name, Chinese name, Mainland Chinese name, and source website.
- License: Taiwan Open Government Data License, version 1.0, `https://data.nat.gov.tw/license`.
- Candidate disciplines: computing, mechanical, chemical engineering, environmental protection, and other NAER academic-terminology datasets selected explicitly in a future intake unit.

## Permitted Englex role

NAER may provide development-time candidates for an English canonical term, Traditional-Chinese label, discipline label, and source provenance. It does not replace the Englex curated layer's original Traditional-Chinese engineering explanation, alias review, context-required decision, abbreviation decision, status, or human acceptance.

## Frozen-snapshot contract

Before a discipline is compared or transformed, the intake evidence must record:

1. dataset catalog URL and direct resource URL;
2. retrieval date, license URL, observed columns, row count, and SHA-256 digest;
3. the selected discipline and inclusion/exclusion reason;
4. normalization, duplicate, conflict, and unmapped counts against the current curated glossary; and
5. the required attribution text for shipped provenance.

No snapshot may be refreshed silently. A changed resource URL, license, schema, or digest begins a new intake unit and requires a new review.

## Prohibited behavior

- No runtime HTTP access, automatic update, query upload, cache, or telemetry.
- No whole-dataset injection into `seed_data.json`.
- No copying a bilingual label as an Englex definition or treating the source as proof of contextual correctness.
- No acceptance, merge, or publication merely because a snapshot passes structural checks.

## Next intake gates

| Gate | Bounded output | Stop condition |
| --- | --- | --- |
| N1 catalog and snapshot audit | One selected NAER discipline snapshot plus the frozen-snapshot evidence | Missing license, fields, or reproducible resource identity |
| N2 deterministic delta | Duplicate, conflict, and unmapped report against the curated layer; no seed changes | Normalization or schema ambiguity |
| N3 curated draft batch | Small draft batch with original Englex meanings and per-entry NAER provenance | Any semantic, abbreviation, or context decision needing human judgment |
| N4 acceptance and import | Only JY-accepted entries enter the curated seed, with regression evidence | No explicit JY batch acceptance |

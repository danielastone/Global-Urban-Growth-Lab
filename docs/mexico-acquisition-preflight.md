# Mexico acquisition preflight

## Purpose

The Mexico locality persistence path must not begin concordance from partially inventoried or truncated source extracts. This preflight separates **source discovery** from **source acquisition** and fails closed until every required wave and geography input is registered.

## Required waves

Population must be registered for 1990, 1995, 2000, 2005, 2010 and 2020. The 1995 and 2005 products are population counts, not censuses, and remain separately identified so transition-specific methodology comparability can be tested later.

SCITEL exposes locality-level geographic identifiers and total population for the historical census/intercensal series. Its national query interface warns that a national result can return only 30,000 records. Therefore an extract is not considered complete merely because it was downloaded from the national option. Acquisition must use state-level files or another demonstrably exhaustive extraction method, and `national_record_cap_avoided` must be true for every acquired row.

## Required supporting evidence

The preflight also requires:

- vintage locality geometry corresponding to every population wave;
- official locality relationship/equivalence evidence;
- locality-history evidence for rekeys, splits, mergers, annexations and municipal transfers.

A current landing page is discovery evidence only. It is not an acquired source row.

## Registration fields

Every acquired input must record an exact source URL or reproducible service query, retrieval date, local path, SHA-256 checksum, license-review status, completeness verification and the record-cap check. The template is `data/mexico_acquisition_registry_template.csv`.

`urban_growth.mexico_acquisition.require_mexico_acquisition_ready` raises an error until all six population waves, all six vintage-geometry waves and both support roles are registered as acquired.

## Sequencing

1. Acquire population extracts for all six events without triggering the 30,000-row national cap.
2. Acquire or identify event-vintage locality geometry for all six events.
3. Export official equivalence relationships and locality-history evidence.
4. Hash files before normalization and complete the registry.
5. Run the acquisition preflight.
6. Only then construct transition-level concordances and measure count- and population-weighted coverage.
7. Only transitions passing geography and methodology checks may enter the persistence forecast panel.

No Mexico empirical result or G2 pass should be registered from the template itself.

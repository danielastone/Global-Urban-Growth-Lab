# Mexico acquisition block — 2026-08-31

## Status

Actual INEGI source acquisition was attempted on 2026-08-31 after the Mexico acquisition preflight gate was merged. No source file is registered as acquired by this note.

Both available external-network paths failed before any INEGI payload could be retrieved:

- the browsing/search layer returned service-unavailable errors for INEGI searches and direct opens;
- direct HTTPS from the execution environment failed DNS resolution for `www.inegi.org.mx`.

Because no official payload was retrieved, no SHA-256, byte count, exact download URL, schema, or completeness claim is recorded. The acquisition registry must remain unresolved.

## Required population extraction sequence

Population events remain 1990 census, 1995 population count, 2000 census, 2005 population count, 2010 census, and 2020 census.

For each event, prefer an official bulk file. If SCITEL is the only viable path, extract all 32 states separately or use another demonstrably exhaustive partition. Do not rely on a single national SCITEL query unless INEGI documentation and observed result counts establish that the result is not subject to the 30,000-record cap.

Each extraction must record event year/type, exact official URL or reproducible query settings, retrieval date, untouched local path, file size, SHA-256, row count, state coverage, locality-key uniqueness diagnostics, total-population field, suppression/aggregate rows, completeness evidence, and license review.

## Completeness test

A population wave may be marked `completeness_verified=true` only if all expected state partitions are present and no partition is known to have hit a query/export cap. Concatenation must preserve every raw row before exclusions. Duplicate locality keys, aggregate rows, missing state partitions, or unexplained count differences must fail the preflight rather than be silently repaired.

## Next successful-network action

1. Retrieve 2020 first using the official bulk or state-partition route.
2. Preserve the raw payload unchanged and hash it.
3. Confirm the locality identifier and total-population field from the file itself.
4. Verify national completeness before scaling the method backward to 2010, 2005, 2000, 1995 and 1990.
5. Only after all six population events clear completeness should relationship/history and vintage-geometry acquisition advance to concordance measurement.

This block is operational, not a relaxation of the Mexico preflight gate.

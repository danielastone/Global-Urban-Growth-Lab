# GHSL fixed-boundary persistence fitness decision

## Decision

The GHSL R2024A v1.2 thematic stream has enough multi-origin coverage and an internally stable geographic unit to exercise the fitness-gated persistence benchmark. It is admitted only as a **retrospective stable-footprint sensitivity**, not as headline or deployable-at-origin evidence.

It is also **not an independent replication of real-world city-growth persistence**. Historical population inside each footprint is a modeled spatial allocation of census/administrative population using GHSL built-up information. The built-up time series is itself modeled from multitemporal satellite observations. See `docs/ghsl-construction-lineage-audit.md` and the empirical red-team result in `docs/ghsl-redteam-130-result-2026-09-01.md`.

## Why this source can enter the persistence benchmark

Every historical GHSL thematic statistic is calculated inside the same 2025 urban-centre footprint. The repository reconciles the fixed thematic and multi-temporal streams at their common 2025 epoch, requiring one-to-one identifier/country agreement, exact area agreement, and population agreement within publisher rounding precision.

That reconciliation is a **current-epoch file/key/version integrity check**, not independent evidence that the fixed and dynamic historical entities are temporally comparable. The fixed 2025 and MTUC 2025 identities are publisher-aligned by construction.

Within the fixed stream, population growth is geographically stable for the narrow retrospective question: how well does recent population change inside today's footprint predict later population change inside that same footprint?

The source-specific fitness adapter therefore requires:

- `boundary_mode = fixed`;
- `boundary_product = ucdb_fixed_2025_boundary`;
- `boundary_reference_year = 2025`;
- `boundary_temporally_fixed = true`;
- `boundary_history_uses_future_reference = true`;
- completed 2025 fixed/dynamic integrity reconciliation.

Rows satisfying those conditions can be `growth_eligible` for retrospective sensitivity analysis.

## Why this is not headline forecast evidence

The fixed polygon is defined using 2025 settlement extent. An analyst standing at an earlier forecast origin would not have known that future footprint. Geography therefore leaks future information even though population outcomes themselves remain chronologically separated.

For that reason the source-specific adapter forcibly sets:

- `headline_eligible = false`;
- `deployable_at_origin = false`;
- `boundary_information_leakage = true`;
- `benchmark_interpretation = retrospective_stable_footprint_sensitivity`.

A good persistence result here establishes only that persistence survives **within the GHSL fixed-footprint modeled population surface**. It does not establish a deployable historical forecast, an independent demographic replication, or the real-world magnitude of persistence.

## Issue #130 empirical red team

The issue #130 rerun materially refines the earlier construction concern.

First, the fixed archive is indeed a hindsight-selected 2025 survivor universe. Requiring MTUC centre birth year to be no later than the forecast origin and fixed-footprint population to be at least 50,000 at the origin retains only 53.8% of centres in 1985, increasing to 90.5% by 2015. Population coverage is much higher, from 89.3% to 98.3%. This selection problem is therefore large by entity count but does not explain away persistence: strong fixed-footprint persistence remains after the origin-defined filter.

Second, a built-up source-process diagnostic does not support the strongest version of the claim that population persistence is merely the built-up allocator showing through. Residualizing recent and future population growth on corresponding built-up growth leaves substantial persistence at every 1985–2015 origin and sometimes increases it. This does **not** validate the residual as true demographic persistence; it only rejects that simple internal explanation.

Third, the pre-2020 cross-source comparison is highly informative. WUP reference-estimate and dynamic-boundary GHSL persistence errors are almost identical from 1985 through 2015, and their persistence-versus-leave-city-out-country MAE ranking agrees at every origin, including the same 2000 reversal. Fixed-footprint GHSL has the same broad ranking pattern but much smaller errors. The earlier description of a WUP/GHSL `unexplained state dependence` should therefore be retired: the unusual strength of fixed GHSL is primarily a fixed-footprint construction/smoothing sensitivity, while the distinctive cross-source disagreement is concentrated in the modeled 2020→2025 endpoint and should be treated as publisher/forward-method sensitivity.

## Construction-lineage threat

GHSL population grids distribute census or administrative-unit population across space using built-up information. For a fixed urban-centre footprint, historical population is therefore not a direct census enumeration of that footprint. The issue #130 internal diagnostics narrow but do not remove this concern.

The matched fixed-versus-dynamic comparison demonstrates that construction choices materially change error magnitude: fixed footprints are substantially smoother and persistence errors are materially smaller than on matched dynamic-footprint rows. That is evidence of **construction sensitivity**, not proof that either footprint recovers the latent demographic process more accurately.

The required external falsification remains a direct-count comparison using national census locality/place histories and defensible concordances. Until then, GHSL cannot upgrade H1 beyond the support available from direct-count or vintage-correct sources.

## Remaining selection problem

The fixed thematic archive contains the 2025 quality-controlled urban-centre universe measured backward through time. This is a future-survivor cohort by construction. The issue #130 origin-defined sensitivity is the appropriate threshold-style comparison, but it still uses future-defined fixed geometry and publisher 2025 birth metadata, so it remains retrospective and non-headline.

GHSL multi-temporal histories are not automatically headline-capable either: active population observations are threshold-selected and polygons change through time. WUP F21 is also threshold-truncated. Neither should be promoted merely because it offers more forecast origins.

## Execution

The original fixed sensitivity remains reproducible with:

```bash
uv run --locked python scripts/run_ghsl_fixed_fitness_persistence.py
```

Issue #130 diagnostics are reproduced with:

```bash
uv run --locked python scripts/run_ghsl_redteam_130.py
```

The dedicated GitHub Actions workflow acquires the official GHSL and WUP inputs and registers source hashes. Historical outputs are preserved rather than silently replaced.

## Next evidence requirement

The next headline-capable persistence result requires a source with multiple historical origins whose geographic identity can be established without future-boundary information and whose threshold/survivorship exposure is acceptable for the intended claim. National census locality concordances remain the preferred route and are now the decisive test of whether persistence of comparable magnitude survives in direct observed locality counts.

# GHSL fixed-boundary persistence fitness decision

## Decision

The GHSL R2024A v1.2 thematic stream is the first repository source with enough multi-origin coverage and an internally stable geographic unit to exercise the fitness-gated persistence benchmark. It is admitted only as a **retrospective stable-footprint sensitivity**, not as headline or deployable-at-origin evidence.

## Why this source can enter the persistence benchmark

Every historical GHSL thematic statistic is calculated inside the same 2025 urban-centre footprint. The repository has already reconciled the fixed thematic and multi-temporal streams at their documented common 2025 epoch, requiring one-to-one identifier/country agreement, exact area agreement, and population agreement within publisher rounding precision.

That makes within-entity population growth geographically stable for the narrow question: how well does recent population change inside today's footprint predict later population change inside that same footprint?

The source-specific fitness adapter therefore requires:

- `boundary_mode = fixed`;
- `boundary_product = ucdb_fixed_2025_boundary`;
- `boundary_reference_year = 2025`;
- `boundary_temporally_fixed = true`;
- `boundary_history_uses_future_reference = true`;
- completed 2025 fixed/dynamic cross-stream reconciliation.

Rows satisfying those conditions can be `growth_eligible` for retrospective sensitivity analysis.

## Why this is not headline forecast evidence

The fixed polygon is defined using 2025 settlement extent. An analyst standing at a 1985, 1990, or 2000 forecast origin would not have known that future footprint. Geography therefore leaks future information even though population outcomes themselves remain chronologically separated.

For that reason the source-specific adapter forcibly sets:

- `headline_eligible = false`;
- `deployable_at_origin = false`;
- `boundary_information_leakage = true`;
- `benchmark_interpretation = retrospective_stable_footprint_sensitivity`.

The runner repeats these labels on every metrics/error output. A good persistence result here would establish that the persistence signal survives a stable-footprint definition. It would **not** establish a deployable historical forecast or remove survivorship concerns.

## Remaining selection problem

The fixed thematic archive contains the 2025 quality-controlled urban-centre universe measured backward through time. This is a future-survivor cohort by construction. The fitness mapping records `survivorship_exposure = material`. The common headline gate therefore rejects it independently of the future-boundary override.

GHSL multi-temporal histories are not an escape from this issue: their active population observations are threshold-selected at 50,000 and their polygons change through time. WUP F21 is also threshold-truncated below 50,000. Neither should be promoted merely because it offers more forecast origins.

## Execution

With the already registered raw GHSL thematic and MTUC files available locally:

```bash
uv run --locked python scripts/run_ghsl_fixed_fitness_persistence.py
```

The script rebuilds both streams, validates their 2025 reconciliation, constructs fixed-boundary forecast intervals, applies the City Data Fitness gate, and then runs only the locked persistence-stage baseline ladder. Generated files remain under `outputs/` and are not committed as empirical claims without result-manifest registration.

## Next evidence requirement

After this sensitivity path, the next headline-capable persistence result still requires a source with multiple historical origins whose geographic identity can be established without future-boundary information and whose threshold/survivorship exposure is acceptable for the intended claim. National census locality concordances remain the preferred route for that test.

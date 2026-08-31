# Urban Growth Research Instructions

This repository is governed by a falsification-first research design for explaining and forecasting city population growth.

## Core rules

1. Separate predictive relationships from causal claims.
2. Preserve geographic identity before estimation. Changing polygons, annexations, mergers, splits, renamed jurisdictions, or reclassification must not masquerade as growth.
3. Treat the 50,000 population threshold as a selection problem. Test truncation, survivorship, entry, exit, and threshold sensitivity using earlier-period population where possible.
4. Make persistence the forecasting benchmark. New variables must earn their complexity through genuine out-of-sample improvement over simple baselines.
5. Separate absolute population size from national city rank.
6. Model expected growth, conditional variance, and downside risk separately.
7. Account for shared dependence across countries, regions, sources/origins, and overlapping spatial structures. Document bootstrap dependence assumptions.
8. Classify results explicitly as descriptive, predictive, quasi-causal, or causal.
9. Prefer geographically validated stable samples for headline results. Less certain concordances belong in robustness analyses only.
10. Preserve a complete evidence chain from raw source through validation, model, robustness test, and claim.

## Immediate empirical order

Do not broaden the project with expensive or weakly observed variables until the following sequence is completed:

1. geographic and temporal validation;
2. City Data Fitness Standard;
3. persistence-only out-of-sample benchmarks;
4. size and rank conditional on persistence and survivorship correction;
5. conditional growth volatility by size/rank;
6. spatial exposure;
7. network accessibility and incremental predictive value.

## City Data Fitness Standard

The executable standard is defined in `src/urban_growth/data_fitness.py` and documented in `docs/city-data-fitness-standard.md`.

Never create a single composite quality score. Fitness is analysis-specific. At minimum preserve separate eligibility for:

- population-level analysis;
- growth-rate analysis;
- spatial/network analysis;
- headline analysis.

Questionable records must remain auditable. Preserve raw values, transformations, exclusions, and machine-readable reasons. Never silently repair a questionable observation.

## Governing principle

Prefer a simple model that survives geographic validation, selection correction, dependence-aware inference, and out-of-sample testing over a sophisticated model whose apparent explanatory power comes from unstable boundaries, leakage, endogenous controls, or in-sample fit.

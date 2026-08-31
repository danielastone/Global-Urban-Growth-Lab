# Fitness-gated persistence-only out-of-sample benchmark

## Purpose

This stage tests whether a city's recent growth contains genuine forecasting information after geographic and temporal fitness screening. It is deliberately simple: persistence must earn its place before size, rank, spatial exposure, or network variables are added.

## Eligibility gate

Forecast rows are not implicitly accepted. The forecasting layer requires an explicit boolean eligibility field produced by a source-specific application of the City Data Fitness Standard. The default is `growth_eligible`; headline analyses may instead require `headline_eligible`.

Missing eligibility is an error. Rows marked false are removed before any training/test split, baseline estimation, or scoring. The gate name and enforcement status are written into benchmark outputs.

## Rolling-origin requirement

A persistence benchmark is genuinely out of sample only when earlier completed outcomes can train the benchmark and later origins can be tested chronologically. The implementation therefore requires at least two usable rolling origins after fitness screening.

The U.S. Census 2010–2020 threshold pilot has only one registered interval. It can validate source ingestion, geographic concordance, threshold selection, and the fitness gate, but it cannot by itself identify persistence out-of-sample performance. The code must raise rather than relabel that single interval as OOS evidence.

## Locked simple baseline ladder

The persistence stage retains only simple baselines already implemented in `urban_growth.forecast`:

- zero growth;
- recent city growth (`persistence`);
- leave-city-out country mean when available;
- leave-city-out region and subregion means when available;
- leave-city-out national Cities-category recent growth when available.

No size, rank, density, built-form, spatial, accessibility, or socioeconomic covariates belong in this stage.

## Leakage rule

For origin `t`, training rows must have `period_end <= t`, while test rows must start at `t`. Ineligible rows are removed before those chronological splits. The implementation uses the existing rolling-origin and leave-city-out baseline primitives rather than creating a second forecast engine.

## Metrics

The benchmark inherits the common matched-row metrics:

- MAE;
- RMSE;
- median absolute error;
- bias;
- directional accuracy.

Row-level errors are retained for later size/rank, downside, country, and region decompositions, but those decompositions must not change the persistence-stage model specification.

## Next empirical execution

The next dataset used for a registered persistence result must satisfy both conditions:

1. source-specific City Data Fitness evidence has been mapped into the common eligibility fields; and
2. at least two chronological forecast origins remain after the gate.

Until then, this stage is implemented and testable but no new persistence result should be claimed from the U.S. single-interval census pilot.

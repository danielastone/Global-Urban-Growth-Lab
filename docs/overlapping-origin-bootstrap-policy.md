# Overlapping-origin bootstrap dependence policy

## Problem

Rolling forecast origins can overlap in outcome windows. For example, a 10-year forecast evaluated every 5 years reuses part of the same realized city trajectory in adjacent forecast outcomes. Annualizing growth does not remove that dependence.

The existing `two_way_cluster_bootstrap_paired_difference` resamples countries and origins independently. Country resampling preserves each country's complete nested city-by-origin contribution, but origin resampling treats origins as exchangeable clusters and does not preserve adjacent temporal blocks. That estimator remains useful as a diagnostic, but it is not the primary pooled inference procedure when forecast windows overlap.

## Locked rule

For pooled paired-error inference across multiple origins:

- declare the forecast horizon explicitly;
- calculate the minimum spacing between evaluated origins;
- if `forecast_horizon_years > minimum_origin_spacing_years`, classify the origins as overlapping;
- overlapping origins must use the moving-block two-way bootstrap in `src/urban_growth/bootstrap_dependence.py`;
- the exchangeable-origin two-way bootstrap may still be reported as a sensitivity diagnostic, but not as the sole headline uncertainty estimate for overlapping origins.

The block length is derived conservatively as:

`ceil(forecast_horizon_years / minimum_origin_spacing_years)`

capped at the number of observed origins. Time blocks are sampled as circular moving blocks over sorted origins. Countries are still resampled as whole clusters, preserving nested city trajectories within sampled countries.

## Interpretation

This does not make overlapping rolling-origin errors independent. It changes the bootstrap resampling unit so adjacent-origin dependence is retained rather than deliberately broken. With very few origins, uncertainty remains weakly identified and should be described accordingly.

When forecast horizons do not overlap, block length is one and the method reduces to exchangeable origin-cluster resampling combined with country-cluster resampling.

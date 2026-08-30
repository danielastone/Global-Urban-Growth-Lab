# Pass 4 audit — bootstrap dependence across overlapping origins

Date: 30 August 2026

## Verdicts

### Q1 — country and origin resampling: PASS WITH LIMITATION

The two-way bootstrap resamples whole countries. Each country draw carries the
country's complete city-by-origin matrix, preserving arbitrary dependence among its
cities and across their origins. Because every city is nested in a country, the
shared-boundary mechanism does not require an additional city cluster to preserve
same-city adjacent-origin correlation.

Origins are independently weighted as exchangeable clusters. That dimension captures
common shocks shared across countries at an origin, but it does not preserve temporal
adjacency as a block characteristic. This is an explicit limitation, not evidence
that the registered interval is too narrow.

### Q2 — absence of city resampling: PASS

No CI-producing bootstrap separately resamples cities. That is appropriate under the
registered country-cluster estimand: country is a broader cluster containing every
city trajectory. Adding a nested city draw would require an additional assumption
that observed cities are exchangeable within country and would not automatically
produce more conservative inference.

### Q3 — temporal reversal diagnostics: NOT RESPONSIVE

`temporal_reversal_diagnostics` computes period-specific correlations, persistence
slopes and reversal rates. It neither pools origins nor estimates cross-origin
covariance. It provides no bootstrap-dependence correction.

### Q4 — shared-endpoint documentation: FAIL, remediated

The prior shared-endpoint section examined predictor/outcome arithmetic and model
performance under a five-year gap. It did not address uncertainty dependence across
origins. Research status now separates the model-bias question from the bootstrap
dependence question.

## Magnitude diagnostic

Using registered WUP row-level errors for persistence minus the leave-city-out country
mean, 20,000 draws produced:

| Resampling design | 95% interval | Half-width |
|---|---:|---:|
| Registered country x exchangeable-origin | [-0.416, +0.204] pp | 0.310 pp |
| Country x circular origin blocks, length 2 | [-0.359, +0.128] pp | 0.243 pp |
| Country x circular origin blocks, length 3 | [-0.352, +0.111] pp | 0.231 pp |

All three intervals cross zero. The moving-block alternatives narrow the interval by
roughly 22% to 25%; they do not reveal understated uncertainty. Same-city adjacent-
origin correlations in paired absolute-error differences have a city-pair-weighted
mean of 0.038 and range from -0.289 to +0.259 across adjacent periods.

The disjoint-window errors do not remove all serial dependence and have only six
origins. Their registered half-width is 0.240 pp versus 0.230 pp for two-origin blocks;
the conclusion again does not change. These diagnostics are too sensitive to block
length and too short in time to justify replacing the registered estimator.

# Research status

## Evidence state

The source and transformation pipeline is now reproducible from registered local files, but the baseline results below remain **retrospective current-revision tests**. They do not yet include block-bootstrap uncertainty, size-stratified performance, balanced-cohort sensitivity, or vintage-correct inputs. They are evidence, but not sufficient for a commercial forecasting claim.

## First rolling-origin baseline result

The evaluation uses five-year WUP estimate outcomes at origins from 1985 through 2020. Every model is scored on the same 67,219 origin-city test cases in aggregate. Metrics are annual growth errors; the table converts them to percentage points per year.

| Baseline | Weighted MAE | Pooled-equivalent RMSE | Interpretation |
|---|---:|---:|---|
| Persistence | 1.337 pp | 2.338 pp | Lowest overall MAE, but relatively poor large-error performance |
| Country historical mean | 1.454 pp | 2.164 pp | Best overall RMSE and strongest non-persistence baseline |
| Global historical mean | 1.591 pp | 2.261 pp | Weaker than country mean, better RMSE than persistence |
| Zero growth | 1.733 pp | 2.557 pp | Weakest overall baseline |

Persistence does not win consistently. Relative to the best simple non-persistence baseline, its MAE is lower at six origins but higher at two:

| Origin | Persistence MAE | Best simple MAE | Persistence change |
|---:|---:|---:|---:|
| 1985 | 1.002 pp | 1.341 pp | 25.3% lower |
| 1990 | 1.616 pp | 1.715 pp | 5.8% lower |
| 1995 | 1.239 pp | 1.721 pp | 28.0% lower |
| 2000 | 1.598 pp | 1.323 pp | 20.9% higher |
| 2005 | 0.989 pp | 1.318 pp | 25.0% lower |
| 2010 | 1.157 pp | 1.450 pp | 20.2% lower |
| 2015 | 1.356 pp | 1.640 pp | 17.3% lower |
| 2020 | 1.654 pp | 1.016 pp | 62.7% higher |

## Hypothesis implications

H1, as preregistered in the README, requires recent growth to improve held-out MAE/RMSE consistently across periods and regions. The first period-level point estimates fail that condition: persistence loses at 2000 and 2020 and has worse pooled-equivalent RMSE than the country and global means. H1 is therefore **not supported in its current universal form**. It must not be restated as “recent growth is the most valuable metric.”

A narrower regime-dependent hypothesis is plausible—persistence often improves typical absolute error but can fail sharply around reversals or common shocks. That is a new hypothesis to test with size strata, country blocks, shock-period indicators and paired uncertainty; it cannot be substituted retroactively for H1.

## Prespecified size-bin comparison

The paired comparison uses the README's existing size bins and compares persistence with country mean on the same city-origin rows. The pooled results do not support a claim that persistence is especially valuable for smaller cities:

| Origin population | N | Persistence MAE | Country-mean MAE | Difference |
|---|---:|---:|---:|---:|
| 50–150k | 43,468 | 1.333 pp | 1.484 pp | −0.151 pp |
| 150–250k | 10,338 | 1.470 pp | 1.495 pp | −0.025 pp |
| 250–500k | 7,167 | 1.401 pp | 1.379 pp | +0.022 pp |
| 500k–1m | 3,389 | 1.178 pp | 1.298 pp | −0.120 pp |
| 1–2m | 1,529 | 1.017 pp | 1.276 pp | −0.258 pp |
| 2m+ | 1,328 | 0.855 pp | 1.160 pp | −0.306 pp |

Negative differences favor persistence. The strongest pooled improvement occurs above one million, not among the smallest observed cities. The 250–500k bin has slightly worse mean error under persistence even though its median paired difference favors persistence, indicating a tail-error problem.

More importantly, the 2000 and 2020 persistence failures span every size bin on mean error. In 2020, persistence loses even for cities above two million. Size composition therefore does not explain the period reversal. The next test should focus on time shocks and country-clustered paired uncertainty, not add an arbitrary size interaction to rescue H1.

## Country-clustered paired uncertainty

The bootstrap resamples whole countries 2,000 times with seed `20260827`, preserving all sampled cities and origins within each national cluster. This materially changes the strength of several point-estimate conclusions.

Pooled by size, the 95% intervals for the persistence-minus-country MAE difference are:

| Origin population | Difference | 95% country-clustered interval | Conclusion |
|---|---:|---:|---|
| 50–150k | −0.151 pp | [−0.244, −0.046] pp | Persistence improvement supported |
| 150–250k | −0.025 pp | [−0.113, +0.092] pp | Unresolved |
| 250–500k | +0.022 pp | [−0.094, +0.130] pp | Unresolved |
| 500k–1m | −0.120 pp | [−0.254, +0.009] pp | Unresolved at 95% |
| 1–2m | −0.258 pp | [−0.334, −0.156] pp | Persistence improvement supported |
| 2m+ | −0.306 pp | [−0.447, −0.207] pp | Persistence improvement supported |

The 2020 reversal is robust: all six size-bin intervals are entirely above zero, including [+0.310, +1.010] pp for 50–150k and [+0.059, +0.577] pp for 2m+. By contrast, all six 2000 intervals cross zero. The correct conclusion is therefore not that persistence failed definitively in two periods; it failed decisively in 2020, while the 2000 point estimates are too country-dependent to distinguish from no difference.

This still falsifies universal H1, because one broad and statistically supported period reversal is enough to defeat “consistent across periods.” It also narrows the next question: identify what changed in the 2015–2020 predictor window and 2020–2025 outcome window, without automatically labeling the effect COVID or claiming causation.

## Temporal decomposition of the 2020 reversal

The reversal is not a uniform decline in city growth. Mean annual growth rises from 0.695% in 2015–2020 to 0.992% in 2020–2025, so persistence underpredicts on average. Its larger failure is cross-city: the association between recent and future growth collapses and more cities switch growth direction.

| Origin | Mean recent growth | Mean future growth | Pearson correlation | Within-country correlation | Persistence slope | Sign reversal rate |
|---:|---:|---:|---:|---:|---:|---:|
| 2000 | 1.795% | 1.265% | 0.488 | 0.383 | 0.329 | 17.8% |
| 2015 | 1.359% | 0.544% | 0.577 | 0.554 | 0.608 | 23.3% |
| 2020 | 0.695% | 0.992% | 0.207 | 0.123 | 0.126 | 29.4% |

The 2015 origin is primarily a broad slowdown: average growth falls sharply while city rankings remain moderately persistent. The 2020 origin instead shows strong mean reversion and reordering even after removing country means. A country-average forecast can therefore outperform city persistence because the city-specific signal becomes unstable, not because all countries or cities share a common decline.

These are descriptive current-revision results, not causal identification. The five-year windows, WUP revisions and lack of contemporaneous covariates do not justify labeling the mechanism COVID. The next independent test should locate influential countries and cities and check whether the collapse survives balanced-cohort and stable-boundary restrictions.

## Reproduction

With the four registered WUP workbooks under `data/raw/`, run:

```bash
python scripts/run_wup_baselines.py
```

The command writes baseline metrics, paired size comparisons, country-clustered bootstrap intervals, and temporal reversal diagnostics under `outputs/`. Raw workbooks and generated outputs remain outside Git.

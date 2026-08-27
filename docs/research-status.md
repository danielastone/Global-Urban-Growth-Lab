# Research status

## Evidence state

The source and transformation pipeline is reproducible from registered local files, but all results remain **retrospective current-revision tests**. The WUP and GHSL exercises use different city definitions and must not be pooled. WUP supplies demographic city records without a verified stable-polygon restriction. GHSL supplies a balanced panel calculated inside fixed 2025 polygons, but that definition uses future geographic information and is not vintage-correct. Neither is sufficient for a commercial forecasting claim.

## Geography-controlled result

The GHSL fixed-boundary workflow uses all 11,422 quality-controlled urban-centre polygons at every five-year epoch. Historical population and built-up values are calculated inside the same 2025 polygon. The executable workflow also reconciles the fixed and multi-temporal products at their common 2025 point before forecasting; mismatched identifiers, countries, population beyond rounding tolerance, built-up area or polygon area fail validation.

Across 91,376 rolling test cases, persistence is strongest on both MAE and RMSE:

| Baseline | Weighted MAE | Pooled-equivalent RMSE |
|---|---:|---:|
| Persistence | 0.879 pp | 1.882 pp |
| Country historical mean | 1.557 pp | 2.366 pp |
| Global historical mean | 1.765 pp | 2.555 pp |
| Zero growth | 1.960 pp | 2.981 pp |

Persistence has the lowest MAE at every evaluated origin. In 2020 its MAE is 0.826 pp, versus 1.081 pp for zero growth, 1.591 pp for country mean and 1.718 pp for global mean. Recent/future growth correlation remains 0.747 overall and 0.750 after country demeaning; the sign-reversal rate is 16.0%. The WUP-specific 2020 collapse therefore does not reproduce when polygon geography is held constant.

This does **not** prove changing WUP polygons caused the discrepancy. GHSL and WUP also differ in settlement definition, gridded population allocation, revision process and sample construction. The defensible conclusion is narrower: the 2020 reversal is source/definition-sensitive and cannot support a general forecasting claim.

## WUP rolling-origin baseline result — geography not controlled

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

H1, as preregistered in the README, requires recent growth to improve held-out MAE/RMSE consistently across periods and regions. WUP period-level estimates fail that condition, while GHSL fixed-boundary estimates support persistence at every period. H1 is therefore **source-sensitive and not supported in its universal form**. It must not be restated without naming the urban definition and boundary treatment.

A narrower regime-dependent hypothesis is plausible—persistence often improves typical absolute error but can fail sharply around reversals or common shocks. That is a new hypothesis to test with size strata, country blocks, shock-period indicators and paired uncertainty; it cannot be substituted retroactively for H1.

## Endogeneity audit: focal-city contamination

The original country historical mean includes the focal city's own earlier growth observations. That is legitimate forecast-origin information, but it mechanically mixes city persistence into the benchmark and is unsuitable for interpreting a distinct country component. A leave-city-out version subtracts every historical observation for the test city from both its country numerator and denominator; where no other country history exists, it uses a global mean that also excludes the focal city.

| Panel | Standard country MAE | Leave-city-out MAE | Mechanical advantage |
|---|---:|---:|---:|
| WUP | 1.454 pp | 1.466 pp | 0.012 pp |
| GHSL fixed polygons | 1.557 pp | 1.570 pp | 0.013 pp |

The standard country mean is slightly optimistic, especially at early origins with shorter histories. The effect is too small to change any headline comparison. At WUP's 2020 origin, leave-city-out MAE is 1.0167 pp versus 1.0162 pp conventionally—a difference of only 0.0005 pp. Mechanical focal-city aggregation therefore does not explain the WUP reversal or the WUP–GHSL disagreement.

This result addresses one narrow endogeneity channel, not the entire problem. The next priority is shared-endpoint measurement error. Recent growth uses \(\log(P_t)-\log(P_{t-5})\), while the outcome uses \(\log(P_{t+5})-\log(P_t)\). An error or revision in \(P_t\) enters the predictor positively and the outcome negatively, mechanically inducing apparent mean reversion. Disjoint-window and alternative-source tests are required before interpreting persistence slopes structurally.

## Endogeneity audit: shared endpoint

The disjoint-window diagnostic inserts a five-year gap. Recent growth remains \(t-5\) to \(t\), but the outcome is \(t+5\) to \(t+10\). The predictor and outcome therefore share no population observation. Comparisons use origins 1990–2015, for which an earlier completed gapped interval is available for training and estimate outcomes remain available.

| Panel and design | Persistence MAE | Leave-city-out country MAE | Persistence RMSE | Leave-city-out country RMSE |
|---|---:|---:|---:|---:|
| WUP adjacent, eligible origins | 1.311 pp | 1.573 pp | 2.292 pp | 2.305 pp |
| WUP five-year gap | 1.644 pp | 1.458 pp | 2.653 pp | 2.098 pp |
| GHSL fixed adjacent, eligible origins | 0.943 pp | 1.604 pp | 1.920 pp | 2.498 pp |
| GHSL fixed five-year gap | 1.321 pp | 1.656 pp | 2.307 pp | 2.396 pp |

Removing the shared endpoint weakens persistence, as expected when the predictor is made five years more remote. In WUP it changes the pooled ranking: country mean beats persistence on both MAE and RMSE. In fixed GHSL, persistence retains the best pooled MAE and RMSE, but loses period-level MAE at 1995 and narrowly at 2010. Persistence is therefore horizon- and source-dependent even when polygons are fixed.

The 2020–2025 target permits a more focused comparison. WUP's adjacent design uses 2015–2020 growth and has persistence MAE 1.654 pp and recent/future correlation 0.207. The gapped design uses 2010–2015 growth, shares no 2020 endpoint, and still loses: persistence MAE is 1.402 pp versus 1.026 pp for country mean, with correlation only 0.327. Removing the shared endpoint improves association but does not eliminate the failure. In fixed GHSL, the corresponding gapped persistence MAE is 1.017 pp versus 1.081 pp for the best alternative, and correlation remains 0.719.

The diagnostic cannot isolate measurement-error bias because inserting a gap also changes predictor recency and the information set. It rejects the stronger claim that the WUP reversal is merely shared-endpoint arithmetic. The unresolved issue is state dependence: why WUP city growth from either 2010–2015 or 2015–2020 transfers poorly into 2020–2025 while fixed-polygon GHSL growth transfers substantially better.

## Endogeneity audit: frozen size and rank

Within-country population rank and city count are calculated from every city observed in the source at the lag or origin year **before** filtering for a future outcome. This prevents future sample survival from determining historical hierarchy. Rank percentile is then compared in two country-fixed-effect specifications: origin hierarchy uses size and rank at \(t\), while frozen hierarchy uses their values at \(t-5\), before the recent-growth window. Both retain recent growth and use the leave-focal-city-out country mean as the prediction anchor.

| Panel and model | Weighted MAE | Pooled-equivalent RMSE |
|---|---:|---:|
| WUP: country-adjusted recent growth | 1.2081 pp | 1.9332 pp |
| WUP: plus origin size/rank | 1.2094 pp | 1.9337 pp |
| WUP: plus frozen size/rank | 1.2099 pp | 1.9336 pp |
| GHSL fixed: country-adjusted recent growth | 0.9468 pp | 1.7655 pp |
| GHSL fixed: plus origin size/rank | 0.9488 pp | 1.7222 pp |
| GHSL fixed: plus frozen size/rank | 0.9507 pp | 1.7250 pp |

Size and rank do not improve pooled MAE in either source. In WUP they also do not improve RMSE. In fixed GHSL they reduce RMSE by about 0.04 pp while slightly worsening MAE, consistent with limited tail-error information rather than broad accuracy gains. Origin and frozen hierarchy differ by less than 0.012 pp MAE in every period; neither timing convention dominates consistently.

The correct conclusion is not that hierarchy has been proven irrelevant or exogenous. The current linear specification finds no material incremental typical-error value after country effects and recent growth, and no sign that using endogenously updated origin rank creates a large forecast advantage over frozen rank. Country-clustered paired uncertainty and nonlinear rank-depth interactions remain required before interpreting the small RMSE change.

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

Within WUP, this defeats universal H1 because one broad and statistically supported period reversal is enough to violate “consistent across periods.” The fixed-polygon GHSL result does not reproduce that reversal, so the cross-source conclusion is sensitivity, not a settled global failure or success.

## Temporal decomposition of the 2020 reversal

The reversal is not a uniform decline in city growth. Mean annual growth rises from 0.695% in 2015–2020 to 0.992% in 2020–2025, so persistence underpredicts on average. Its larger failure is cross-city: the association between recent and future growth collapses and more cities switch growth direction.

| Origin | Mean recent growth | Mean future growth | Pearson correlation | Within-country correlation | Persistence slope | Sign reversal rate |
|---:|---:|---:|---:|---:|---:|---:|
| 2000 | 1.795% | 1.265% | 0.488 | 0.383 | 0.329 | 17.8% |
| 2015 | 1.359% | 0.544% | 0.577 | 0.554 | 0.608 | 23.3% |
| 2020 | 0.695% | 0.992% | 0.207 | 0.123 | 0.126 | 29.4% |

The 2015 origin is primarily a broad slowdown: average growth falls sharply while city rankings remain moderately persistent. The 2020 origin instead shows strong mean reversion and reordering even after removing country means. A country-average forecast can therefore outperform city persistence because the city-specific signal becomes unstable, not because all countries or cities share a common decline.

These are descriptive current-revision results, not causal identification. The five-year windows, WUP revisions and lack of contemporaneous covariates do not justify labeling the mechanism COVID. Influence and fixed-boundary tests are now complete; balanced-entry and equal-country weighting remain unresolved.

## Influence diagnostics

The 2020 persistence-minus-country MAE difference is +0.637 percentage points. Leave-one-country-out estimates remain adverse under every one of the 189 exclusions, ranging from +0.505 to +0.693 points. No single-country deletion overturns the result.

| Country excluded | Cities | Sample share | Country mean difference | Difference after exclusion | Shift |
|---|---:|---:|---:|---:|---:|
| India | 1,838 | 17.2% | +1.278 pp | +0.505 pp | −0.133 pp |
| China | 2,002 | 18.7% | +0.396 pp | +0.693 pp | +0.055 pp |
| Brazil | 329 | 3.1% | −0.632 pp | +0.678 pp | +0.040 pp |
| Pakistan | 274 | 2.6% | +1.832 pp | +0.606 pp | −0.031 pp |
| Indonesia | 358 | 3.3% | −0.211 pp | +0.667 pp | +0.029 pp |

India is materially influential because it combines a large sample share with a large persistence penalty. China is even larger but closer to the pooled estimate, and Brazil and Indonesia partially offset the reversal. The conclusion is therefore broad enough to survive country deletion, but the nominal city count is not equivalent to balanced global evidence: India and China alone supply 35.9% of observations.

Single-city influence is negligible at the pooled level. The largest deletion changes the mean difference by only 0.0024 percentage points, and none of 10,709 city deletions changes its sign. Extreme city errors remain useful for source-quality review, but they do not explain the aggregate reversal.

This diagnostic addresses dependence on one observed cluster; it does not repair unequal country representation, threshold selection or common WUP revision error. Balanced-country weighting and balanced-entry cohorts remain separate required tests.

## Reproduction

With the registered raw files under `data/raw/`, run:

```bash
python scripts/run_wup_baselines.py
python scripts/run_ghsl_fixed_baselines.py
```

The commands write separate WUP and fixed-boundary GHSL metrics and diagnostics under `outputs/`. The GHSL command fails unless the fixed and dynamic products reconcile at 2025. Raw files and generated outputs remain outside Git.

The WUP command now writes both origin-by-size and explicitly pooled-by-size paired/bootstrap tables. The pooled files are the direct source for the six-row tables reported above. After both workflows run, verify every default output against the committed hashes and dimensions:

```bash
python scripts/verify_results.py \
  results/wup_expected_manifest.csv \
  results/ghsl_fixed_expected_manifest.csv
```

This closes result drift for the registered local files and locked code. It does not make the raw-data workflows executable in GitHub Actions or convert the retrospective estimates into vintage-correct forecasts.

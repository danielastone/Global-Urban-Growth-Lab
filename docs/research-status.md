# Research status

## Specification implementation status — 29 August 2026

The consolidated quality-review specification is now the repository's governing contract.
Executable utilities enforce forecast-origin-fixed absolute and relative tiers, ordered-tier
ILR eligibility, open interval-censored WUP-entry delay bounds, comparable-geography census
cohorts, mutually exclusive modern travel-time bands, and distinct C1/C2/C3 urban-form timing.

This is implementation of design constraints, not completion of the empirical program. The
dynamic-estimator core and reproducible finite-T simulation runner are implemented, but their
empirical common-sample run and final simulation acceptance thresholds remain open. Country
census pilots, the independent-lineage morphology matrix, modern accessibility raster build,
and national-envelope forecast module also remain open gates in
`docs/locked-specification.md`. No new causal claim follows from merging contract code.

## Dynamic-estimator implementation gate

The locked hierarchy now has a machine-readable registry and one common-sample constructor.
It fits the pooled predictive benchmark, the Nickell-biased city fixed-effect diagnostic, and
a split-panel-jackknife finite-T correction with country-period fixed effects. The first two
return a country-and-period two-way sandwich covariance. The corrected estimator deliberately
returns no analytic standard error. A separate product-exponential multiplier bootstrap
perturbs country and period dimensions independently while preserving city time order and
recomputing the full correction. Runs below 399 replications are marked non-production.

`scripts/run_dynamic_estimator_simulation.py` spans persistence values 0.2, 0.6, and 0.9 and
panel lengths 6, 8, and 10 under a fixed seed. It reports estimator bias and RMSE rather than
assuming the correction improves every draw. Restricted dynamic GMM remains registered but
unimplemented; it is not an automatic fourth model and cannot be run unless instrument-strength
and proliferation gates are specified. Issue #27 remains open until empirical estimates use
identical full-sample rows, the multiplier interval's coverage is evaluated in the declared
simulation grid, and the simulation gate is evaluated at production replication counts. The
presence of a bootstrap interval is not evidence that its finite-sample coverage is adequate.

The coverage gate is now executable through `scripts/run_dynamic_bootstrap_coverage.py` and
was specified before opening a production result. Each persistence-by-panel-length cell needs
at least 200 simulated panels and 399 bootstrap draws. A nominal 95% interval passes only when
the 95% Wilson interval around empirical coverage lies wholly within 90% to 99%; this rejects
both material undercoverage and vacuously wide intervals. Smaller runs return a missing gate
decision rather than a provisional pass. The command accepts repeated `--persistence` and
`--panel-length` arguments so long runs can be split into auditable cells.

Only the split-panel-jackknife estimator is eligible for this structural-persistence coverage
gate. Pooled prediction has a different between-and-within estimand, so coverage of the DGP's
within-city persistence parameter is not a coherent success criterion for it. The uncorrected
city-FE estimator remains a known Nickell-biased diagnostic. Their simulated coverage is
reported, but neither can receive a gate pass. The manual Actions workflow runs the nine locked
cells independently, uploads each artifact, validates the complete 27-row grid, and uploads the
combined result before evaluating the corrected-estimator gate.

The production run at Actions run `33312725082`, head commit
`ba02a4d2f5d2975cef141babf62570c51de917e4`, completed all nine locked cells with 200
simulated panels and 399 bootstrap draws per cell. The eligible half-panel-jackknife interval
covered 200 of 200 panels in every cell. Its Wilson interval was [0.9812, 1.0000] throughout,
which is not wholly inside the prespecified [0.90, 0.99] acceptance band. All nine eligible
cells therefore fail for overcoverage: the interval is too conservative to be treated as
calibrated uncertainty. The pooled and uncorrected city-FE rows remain diagnostic and were
ineligible for this gate; their coverage values are not additional gate failures.

The combined 27-row output is registered in
`results/dynamic_bootstrap_coverage_expected_manifest.csv`. The failed gate is a statistical
result, not a workflow failure to retry. Thresholds were not changed and no claim should use
the jackknife multiplier interval as validated uncertainty pending a separately specified
estimator or interval redesign.

The empirical hierarchy runner now absorbs country-period and city fixed effects by weighted
alternating projections rather than materializing a global city-dummy matrix. Small-panel tests
require absorbed coefficients to match the prior dense weighted and unweighted fits. The WUP
runner also enforces at least two observations per city in each jackknife half and reports the
resulting row and city retention. This makes the common-sample point-estimate comparison
executable, but it increases survivorship selection.

The registered WUP common sample contains 55,793 of 72,857 candidate city-origin rows (76.6%)
and 6,450 of 11,537 candidate cities (55.9%), across 142 of 191 candidate countries. Eligibility
requires at least two observations for a city in each jackknife half. This is a selected panel
of more continuously observed cities, not a correction for threshold entry or survivorship.

| Term | Pooled predictive | City FE diagnostic | Half-panel jackknife |
|---|---:|---:|---:|
| Recent growth | 0.455 | 0.204 | 0.336 |
| Origin log population | 0.001 | -0.032 | -0.023 |
| Origin country-rank percentile | 0.002 | 0.005 | -0.008 |

All three terms trigger the machine-readable disagreement rule. Persistence remains positive,
but its magnitude depends materially on whether stable between-city differences are retained
and whether finite-T bias is corrected. Size and hierarchy change sign across estimators. The
within-city size coefficient is not a causal “size protection” result: current log population
accumulates prior growth, and WUP city definitions change through time. No corrected-estimator
confidence interval passed the production coverage gate, so these are point estimates only.
Selecting one estimator because its sign fits the preferred story is prohibited.

The three outputs are registered in `results/wup_dynamic_hierarchy_expected_manifest.csv`
against producing commit `4314b4c99eaea65f18c958a6ce966434c257e74e`.

## Evidence state

The direct Module A national-envelope pipeline is executable from the registered WUP F01
workbook. It reconciles Cities, Towns, and Rural country totals to the publisher's Total sheet,
constructs 3,555 non-overlapping five-year reallocation intervals on the forecast-origin grid,
separates retrospective outcomes from origin-available forecast features, and produces
country-equal and population-weighted regional/global summaries. The audit flags 85 intervals
(2.39%) for category appearance/disappearance or an absolute category-share change of at least
0.25; summaries retain the complete sample and report a stable-composition sensitivity that
excludes those intervals. A flag is not proof of source error or demographic impossibility.
This is an implementation and numerical-audit result, not evidence that a national envelope
improves city forecasts or a causal interpretation of settlement reallocation. Provenance-bound
outputs are registered in `results/national_envelope_expected_manifest.csv` against producing
commit `a63aa47dcfc385b0fd4ba86813dfb6990ac51b05`. This closes output drift for the reviewed
Module A transformation; predictive evaluation remains open under issue #29.

The source and transformation pipeline is reproducible from registered local files, but all results remain **retrospective current-revision tests**. The WUP and GHSL exercises use different city definitions and must not be pooled. WUP supplies demographic city records without a verified stable-polygon restriction. GHSL supplies a balanced panel calculated inside fixed 2025 polygons, but that definition uses future geographic information and is not vintage-correct. Neither is sufficient for a commercial forecasting claim.

## Fixed-2025-boundary sensitivity

The GHSL fixed-boundary workflow uses all 11,422 quality-controlled urban-centre polygons at every five-year epoch. Historical population and built-up values are calculated inside the same 2025 polygon. The executable workflow also reconciles the fixed and multi-temporal products at their common 2025 point before forecasting; mismatched identifiers, countries, population beyond rounding tolerance, built-up area or polygon area fail validation. This validates the common 2025 cross-stream point and fixed-boundary semantics—not the historical accuracy of a 2025 polygon applied backward.

Across 91,376 rolling test cases, persistence is strongest on both MAE and RMSE:

| Baseline | Weighted MAE | Pooled-equivalent RMSE |
|---|---:|---:|
| Persistence | 0.879 pp | 1.882 pp |
| Country historical mean | 1.557 pp | 2.366 pp |
| Global historical mean | 1.765 pp | 2.555 pp |
| Zero growth | 1.960 pp | 2.981 pp |

Persistence has the lowest MAE at every evaluated origin. In 2020 its MAE is 0.826 pp, versus 1.081 pp for zero growth, 1.591 pp for country mean and 1.718 pp for global mean. Recent/future growth correlation remains 0.747 overall and 0.750 after country demeaning; the sign-reversal rate is 16.0%. The WUP-specific 2020 collapse therefore does not reproduce when polygon geography is held constant.

This does **not** prove changing WUP polygons caused the discrepancy. GHSL and WUP also differ in settlement definition, gridded population allocation, revision process and sample construction. The defensible conclusion is narrower: the 2020 reversal is source/definition-sensitive and cannot support a general forecasting claim.

## Matched fixed-versus-dynamic GHSL sensitivity

The within-GHSL comparison holds source family, identifier, country, forecast origin and row coverage constant. The matched sample grows from 5,061 city-origin rows at 1980 to 10,333 at 2020 as dynamic urban centres enter the threshold-defined universe. Fixed and dynamic populations remain separate estimands: fixed growth occurs inside the 2025 footprint, while dynamic growth includes contemporaneous footprint change.

| Boundary stream | Persistence MAE | Country-mean MAE | Persistence RMSE | Country-mean RMSE |
|---|---:|---:|---:|---:|
| Fixed 2025 footprint, matched rows | 0.758 pp | 1.171 pp | 1.334 pp | 1.660 pp |
| Dynamic footprint, matched rows | 1.274 pp | 1.550 pp | 2.268 pp | 2.220 pp |

Holding the polygon fixed makes growth much smoother and persistence substantially stronger. Under dynamic boundaries, persistence retains the best pooled MAE but loses pooled RMSE narrowly to country mean. Both definitions show a period reversal at 2000. At 2020, persistence still beats the best alternative in both streams: by 0.221 pp under fixed boundaries and 0.071 pp under dynamic boundaries.

Recent/future within-country correlation at 2020 is 0.764 in fixed polygons and 0.532 in dynamic polygons. Boundary evolution therefore weakens city-level state persistence, but it does not reproduce WUP's 2020 collapse or explain the WUP–GHSL disagreement. The remaining discrepancy must lie in the broader source/definition package rather than changing polygons alone.

This matched exercise still has selection: a dynamic centre must exist at every required lag, origin and outcome year, and entry is tied to the 50,000 urban-centre threshold. It isolates boundary semantics better than the cross-source comparison but does not create a balanced historical city universe.

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

### Corrected national-component common sample

Exact-input regeneration found that the F01-minus-F21 national Cities residual is not
positive at both endpoints for 264 city-origin rows across 55 countries. These are not
missing downloads. They include singleton national city systems, one-person rounding
differences, and cross-border urban centres whose F21 population is not a valid
component of the focal country's F01 total. The leave-city-out national comparator is
undefined for those rows. The workflow now flags them, leaves that diagnostic missing,
and scores every baseline on the common finite sample.

At the 2020 origin this removes 25 of 10,709 city rows (0.23%) but 25 of 189 countries
(13.2%). Pooled metrics therefore move little, while equal-country metrics move more.
The substantive ranking does not change:

| 2020 comparison | Historical sample | Corrected common sample |
|---|---:|---:|
| Scored city rows | 10,709 | 10,684 |
| Persistence MAE | 1.654 pp | 1.652 pp |
| Leave-city-out country-mean MAE | 1.017 pp | 1.017 pp |
| Persistence minus country-mean MAE | 0.637 pp | 0.634 pp |
| Best pooled-MAE model | Subregion mean | Subregion mean |

Persistence remains best by pooled MAE at six of eight rolling origins. It remains
worse than the leave-city-out country mean in 2000 and sharply worse in 2020. At the
2020 origin, persistence is worse in every initial-size band; the country-clustered
95% interval for the persistence-minus-country difference remains above zero in all
six bands. The smallest lower bound is 0.045 pp for the 1–2 million band.

Across all eight origins, the two-way country-by-time bootstrap estimates a pooled
persistence-minus-leave-city-out-country difference of -0.129 pp with a 95% interval
from -0.426 to 0.193 pp. The point estimate favors persistence on average, but the
interval crosses zero. The corrected analysis therefore supports a regime-dependent
forecasting signal, not the unconditional claim that recent growth is always or
uniformly the strongest predictor.

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

All hierarchy specifications are now fitted and scored on one joint-complete training frame
and one joint-complete test frame at each origin. The registered WUP inputs lose no rows under
this intersection: candidate and matched counts are identical at every origin, so the numerical
table below is unchanged. The prior implementation nevertheless lacked this invariant and could
have compared different cities if one hierarchy field were missing in another source or revision.
Outputs now record candidate and matched train/test counts and fail if any model loses a row.

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

## Balanced-entry and equal-country sensitivity

The balanced WUP cohort retains only cities with complete forecast intervals at all nine construction origins from 1980 through 2020. It contains 5,152 cities at each of the eight evaluated origins, compared with a changing sample that grows from 6,147 test rows in 1985 to 10,709 in 2020. This is a hindsight-defined sensitivity cohort: inclusion at an early origin depends on survival through later declared origins. It therefore removes later threshold entrants and intermittent coverage, but selects established cities retrospectively known to remain observable and is not a deployable forecast population.

| Cohort | Persistence MAE | Leave-city-out country MAE | Persistence RMSE | Leave-city-out country RMSE |
|---|---:|---:|---:|---:|
| Changing WUP sample, city weighted | 1.337 pp | 1.466 pp | 2.338 pp | 2.179 pp |
| Balanced WUP cohort, city weighted | 1.109 pp | 1.332 pp | 1.905 pp | 1.934 pp |
| Changing WUP sample, countries equal | 1.613 pp | 1.664 pp | 2.964 pp | 2.559 pp |
| Balanced WUP cohort, countries equal | 1.268 pp | 1.555 pp | 2.337 pp | 2.299 pp |

Balancing materially improves persistence MAE and removes its slight pooled RMSE disadvantage under city weighting. Equal-country scoring increases errors because small, volatile country samples receive the same weight as large national samples; persistence retains the best equal-country MAE but not RMSE.

The period result is more important. Under both equal-country variants, persistence beats leave-city-out country mean at the 2000 origin: by 0.134 pp in the changing cohort and 0.227 pp in the balanced cohort. The earlier city-weighted 2000 reversal is therefore composition-sensitive. At 2020, persistence remains decisively worse: by 0.853 pp with changing coverage and 0.695 pp in the balanced cohort. Selection and India/China observation counts do not explain the 2020 failure.

These are point-estimate weighting sensitivities, not new confidence intervals. The balanced cohort cannot answer the small-city question because continuous eligibility preferentially selects cities already above 50,000 throughout the study period.

More importantly, the 2000 and 2020 persistence failures span every size bin on mean error. In 2020, persistence loses even for cities above two million. Size composition therefore does not explain the period reversal. The next test should focus on time shocks and country-clustered paired uncertainty, not add an arbitrary size interaction to rescue H1.

## Country-clustered paired uncertainty

The one-way bootstrap resamples whole countries 2,000 times with seed `20260827`, preserving all sampled cities and origins within each national cluster. It accounts for geographic clustering but treats the eight realized forecast origins as fixed. Its pooled intervals must therefore not be interpreted as evidence of stability across time.

Pooled by size, the 95% intervals for the persistence-minus-country MAE difference are:

| Origin population | Difference | 95% country-clustered interval | Conclusion |
|---|---:|---:|---|
| 50–150k | −0.151 pp | [−0.244, −0.046] pp | Supported conditional on observed periods |
| 150–250k | −0.025 pp | [−0.113, +0.092] pp | Unresolved |
| 250–500k | +0.022 pp | [−0.094, +0.130] pp | Unresolved |
| 500k–1m | −0.120 pp | [−0.254, +0.009] pp | Unresolved at 95% |
| 1–2m | −0.258 pp | [−0.334, −0.156] pp | Supported conditional on observed periods |
| 2m+ | −0.306 pp | [−0.447, −0.207] pp | Supported conditional on observed periods |

The 2020 reversal is robust: all six size-bin intervals are entirely above zero, including [+0.310, +1.010] pp for 50–150k and [+0.059, +0.577] pp for 2m+. By contrast, all six 2000 intervals cross zero. The correct conclusion is therefore not that persistence failed definitively in two periods; it failed decisively in 2020, while the 2000 point estimates are too country-dependent to distinguish from no difference.

Within WUP, this defeats universal H1 because one broad and statistically supported period reversal is enough to violate “consistent across periods.” The fixed-polygon GHSL result does not reproduce that reversal, so the cross-source conclusion is sensitivity, not a settled global failure or success.

## Pooled point-estimate weighting

**Pending regeneration:** existing pooled point estimates are city-origin weighted,
so WUP origins with more eligible cities receive more influence. The workflow now
emits equal-origin and equal-country-within-origin point estimates. Until those
outputs and expected hashes are regenerated, pooled claims should be described by
their city-origin weighting rather than as generic global performance.

## Joint country-and-time uncertainty

The two-way pigeonhole bootstrap independently resamples countries and forecast origins, applying the product of their resampling weights to each country-origin cell. It retains all city errors within a cell and uses the same 2,000 repetitions and seed. This targets sensitivity to both geographic composition and which historical periods were realized.

| Size bin | Difference | Two-way 95% interval |
|---|---:|---:|
| 50–150k | −0.151 pp | [−0.426, +0.165] pp |
| 150–250k | −0.025 pp | [−0.360, +0.344] pp |
| 250–500k | +0.022 pp | [−0.310, +0.516] pp |
| 500k–1m | −0.120 pp | [−0.474, +0.308] pp |
| 1–2m | −0.258 pp | [−0.542, +0.038] pp |
| 2m+ | −0.306 pp | [−0.686, +0.064] pp |

Every size-bin interval crosses zero. The overall persistence-minus-leave-city-out-country difference is −0.129 pp with interval [−0.406, +0.206] pp. In the balanced cohort it is −0.223 pp with interval [−0.466, +0.060] pp. The data therefore do not support a stable pooled persistence advantage across periods, overall or by size.

This does not overturn the 2020 finding. A single-origin comparison has no across-time sampling dimension; its country-clustered intervals remain the relevant uncertainty calculation and remain adverse to persistence in every size bin. With only eight evaluated origins, the two-way intervals are necessarily coarse and should be treated as a warning against pooled generalization rather than precise time-series inference.

## National demographic comparator

**Superseded pending regeneration:** the numerical results immediately below use the
inclusive F01 national Cities-category comparator and should not be treated as the
primary national baseline. The corrected workflow now subtracts the focal F21 city
at both endpoints. New empirical values and expected-output hashes must be generated
from the registered raw files before this section is updated.

The acquired WUP F01 national control now supplies a baseline that was previously
missing: each country's observed growth in the harmonized Cities category over the
five years ending at the forecast origin is carried forward to its sampled cities.
This is not the same as `country_mean`, which is an unweighted historical mean of
sampled city outcomes.

Across the 67,219 WUP evaluation rows, national Cities-category persistence has MAE
1.747 pp and RMSE 2.446 pp. It is worse than city persistence (1.337 pp MAE) and the
leave-city-out country mean (1.466 pp MAE), with a +0.984 pp bias. Equal-country MAE
is also worse at 1.959 pp, compared with 1.613 pp for city persistence. National
aggregate momentum therefore does not explain the pooled city-level signal.

At the 2020 origin, however, the national comparator's MAE is 1.132 pp, well below
city persistence's 1.654 pp but still above the historical country mean's 1.016 pp.
The 2020 city-persistence reversal is thus consistent with a period when national
momentum was more useful than each city's immediately preceding trajectory. It does
not establish a causal national mechanism, and the current WUP revision cannot
reconstruct the information set of an actual pre-2020 forecaster.

This closes the missing national-baseline omission. A vintage-correct national
forecast remains untested.

## Country, subregion, region and global aggregation

The F01 geographic hierarchy now supports a matched aggregation ladder using only
historical training outcomes. Leave-city-out versions remove all earlier outcomes
for the focal city from each aggregate. This matters most for the country baseline;
for regions the self-inclusion effect is numerically negligible.

| Baseline | Pooled MAE | Equal-country MAE |
|---|---:|---:|
| Global mean, leave city out | 1.591 pp | 1.737 pp |
| Region mean, leave city out | 1.492 pp | 1.610 pp |
| Subregion mean, leave city out | 1.454 pp | 1.558 pp |
| Country mean, leave city out | 1.466 pp | 1.664 pp |

Region beats global mean by 0.099 pp. The country-by-time bootstrap interval is
[−0.237, −0.022] pp, so broad regional information adds predictive value beyond a
single global history across these eight origins. Subregion improves on region by
0.038 pp, but its interval [−0.132, +0.067] crosses zero. Country is 0.012 pp worse
than subregion, with interval [−0.036, +0.054] pp; every origin-specific
country-clustered interval also crosses zero.

The implication is uncomfortable but clear: the data support geography above the
global level, but do not show that country history adds predictive value beyond UN
subregions. H4 is therefore rejected in its stronger national-dominance form. This
does not prove that politics or national demography are irrelevant; it shows that
this forecasting design cannot distinguish their incremental contribution from
shared subregional growth patterns. Adding causal language would exceed the design.

## WUP 2018 vintage test

The archived WUP 2018 F22 workbook permits one genuinely vintage-correct predictor
test. On reciprocal within-country geographic matches no farther than 5 km, 1,509
urban agglomerations across 141 countries have complete 2013, 2018 and 2023 values
in both editions. The target is WUP 2025 estimated growth from 2018–2023.

| Predictor available or published in 2018 | MAE | RMSE | Bias |
|---|---:|---:|---:|
| WUP 2018 published projection | 1.268 pp | 1.650 pp | +1.081 pp |
| Persistence calculated from WUP 2018 | 1.494 pp | 1.940 pp | +1.364 pp |
| Persistence recalculated from WUP 2025 | 0.959 pp | 1.499 pp | +0.648 pp |

The published 2018 projection beats the persistence baseline available in 2018 by
0.226 pp. A country-clustered bootstrap gives [−0.270, −0.169] pp. Restricting to the
567 cities whose 2018 populations agree within 20% across revisions produces almost
the same difference, 0.224 pp with interval [−0.277, −0.158] pp.

The annual horizon decomposition shows when that advantage appears:

| Target end | Published projection MAE | Vintage persistence MAE | Revised-history persistence MAE | Published minus vintage persistence, 95% interval |
|---:|---:|---:|---:|---:|
| 2019 | 1.344 pp | 1.380 pp | 0.356 pp | −0.036 pp [−0.097, +0.019] |
| 2020 | 1.332 pp | 1.377 pp | 0.370 pp | −0.045 pp [−0.106, +0.011] |
| 2021 | 1.239 pp | 1.361 pp | 0.613 pp | −0.123 pp [−0.170, −0.073] |
| 2022 | 1.254 pp | 1.433 pp | 0.821 pp | −0.179 pp [−0.222, −0.132] |
| 2023 | 1.268 pp | 1.494 pp | 0.959 pp | −0.226 pp [−0.270, −0.169] |

The published projection is not distinguishable from vintage persistence for targets
ending in 2019 or 2020. Its advantage becomes statistically supported at 2021 and
widens thereafter. That timing is compatible with a pandemic-era shock, but it does
not identify one: the 2018 projection, population definitions and later estimates
all change together across editions.

This timing survives the crosswalk specification. The workflow evaluates reciprocal
matches at 1, 5 and 10 km and, within each radius, no population-agreement restriction
or later-revision agreement within 10%, 20% or 50%. For the 2023 target, the published
projection advantage ranges from 0.219 to 0.285 pp across all 12 combinations, and
every country-clustered interval is entirely below zero. All 12 combinations are also
below zero for 2021 and 2022. For 2019, 11 of 12 intervals cross zero; for 2020, 11 of
12 cross zero. The isolated exceptions occur in nested hindsight-selected samples
and do not justify moving the break earlier.

These are overlapping sensitivity samples, not 12 independent replications. Their
value is falsification: neither coordinate radius nor origin-population agreement
overturns the supported post-2020 ranking or the unresolved pre-2021 ranking.

The matched sample is not representative of the complete vintage universe. Before
requiring a complete later-revision outcome, the primary 5 km rule matches 1,547 of
1,860 F22 agglomerations and excludes 313. Included places average 1.13 million
inhabitants in 2018, versus 2.31 million among exclusions, a standardized mean
difference of −0.41. Differences in prior and published projected growth are small,
but country coverage is uneven: 53 United States, 40 Chinese, 24 Indian, 18
Philippine and 14 South Korean agglomerations are excluded, and 12 countries have no
primary match. The ranking is therefore conditional on geographically matched large
places and underrepresents several large-country and metropolitan-definition cases.
It must not be presented as an estimate for all 1,860 F22 agglomerations.

Unequal country sample sizes do not explain the ranking, although they strengthen its
magnitude. Equal weighting across the 141 matched countries reduces the published
projection advantage from 0.226 to 0.180 pp; the equal-country bootstrap interval is
[−0.280, −0.093] pp. The projection has lower country-level MAE in 97 countries and
persistence in 44. Deleting one country at a time leaves the city-weighted difference
between −0.234 and −0.212 pp. China contributes 381 of 1,509 scored cities, so the
city-weighted estimate should not be called globally representative, but neither
China nor another single country creates the sign of the result.

The more consequential comparison is vintage versus retrospective persistence.
Recomputing persistence with values revised in 2025 lowers apparent MAE by 0.536 pp.
That performance was unavailable to a forecaster in 2018. The current-revision
rolling-origin results therefore materially overstate the real-time value of
persistence for this matched large-city sample.

More importantly, the hindsight advantage already exists for the 2019 target:
revised-history persistence reports 0.356 pp MAE while actual-vintage persistence is
1.380 pp. Definition and historical-series revisions therefore contaminate the
comparison before COVID. The pandemic cannot be the sole explanation for the
vintage-versus-retrospective gap.

This does not make the 2018 projection a clean winner or a small-city result. WUP
2018 uses nationally defined urban agglomerations above 300,000, while WUP 2025 uses
harmonized DEGURBA cities. Only 304 primary matches agree within 10% at the 2018
origin. All three predictors are positively biased against the later target, and the
2018–2023 window includes both definition revisions and the pandemic shock. The
defensible result is narrower: the official vintage forecast robustly beats vintage
persistence on the selected matched large-place sample, while revised-history
persistence receives a large hindsight advantage.

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
python scripts/run_wup2018_vintage.py
python scripts/run_ghsl_fixed_baselines.py
python scripts/run_ghsl_boundary_sensitivity.py
python scripts/run_national_envelope.py
python scripts/run_wup_dynamic_hierarchy.py
```

The commands write separate WUP and fixed-boundary GHSL metrics and diagnostics under `outputs/`. The GHSL command fails unless the fixed and dynamic products reconcile at 2025. Raw files and generated outputs remain outside Git.

The WUP command now writes both origin-by-size and explicitly pooled-by-size paired/bootstrap tables. The pooled files are the direct source for the six-row tables reported above. After both workflows run, verify every default output against the committed hashes and dimensions:

```bash
python scripts/verify_results.py \
  results/wup_expected_manifest.csv \
  results/wup2018_vintage_expected_manifest.csv \
  results/ghsl_fixed_expected_manifest.csv \
  results/ghsl_boundary_expected_manifest.csv \
  results/national_envelope_expected_manifest.csv \
  results/dynamic_bootstrap_coverage_expected_manifest.csv \
  results/wup_dynamic_hierarchy_expected_manifest.csv
```

This closes result drift for the registered local files and locked code. It does not make the raw-data workflows executable in GitHub Actions or convert the retrospective estimates into vintage-correct forecasts.

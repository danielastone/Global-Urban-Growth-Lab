# Research design

## Objective

Estimate realistic out-of-sample accuracy for city population growth, with explicit attention to small-city coverage and measurement error. Explanatory regressions are secondary to forecast validation.

## Outcome

For city `i` from year `t` to `t+h`:

```text
g(i,t,t+h) = [log(population(i,t+h)) - log(population(i,t))] / h
```

Report decimal annual growth and percentage-point equivalents. Do not mix annual and five-year coefficients.

## Baseline ladder

Models must be evaluated in this order:

1. global historical mean;
2. region-period mean available at the forecast origin;
3. country historical mean or national demographic forecast;
4. country historical mean excluding the focal city's history;
5. city persistence (latest observed growth);
6. persistence plus initial log population and hierarchy position;
7. national urbanization and demographic controls;
8. spatial, border, accessibility, and shock extensions.

A complex model earns inclusion only through repeated held-out improvement over the strongest simpler baseline.

The baseline executions show why boundary treatment is binding. In WUP, persistence has the lowest weighted MAE but worse pooled-equivalent RMSE than country and global means, and loses on MAE at 2000 and 2020. Inside fixed GHSL 2025 polygons, persistence has the best MAE and RMSE and wins at every origin. Subsequent models must beat country mean and persistence on matched rows within each declared urban definition; comparison only with zero growth or pooling the two sources is inadequate.

The prespecified size comparison does not explain the 2020 failure: persistence loses across every size bin, and every country-clustered 95% interval excludes zero in the adverse direction. The analogous 2000 point estimates are not statistically resolved after country clustering and reverse under balanced/equal-country weighting. One-way country bootstrap intervals appear to support pooled persistence gains in some sizes, but every such interval crosses zero after origins are also resampled. There is no stable pooled size-specific advantage across time.

WUP temporal diagnostics show that its 2020 failure is not explained by a common slowdown. Mean growth increases from the predictor to outcome window, while recent/future Pearson correlation falls to 0.207, within-country correlation to 0.123, and the fitted persistence slope to 0.126. Direction reversals reach 29.4%. Influence and fixed-boundary tests show that this is not a single-cluster result and does not reproduce in GHSL fixed polygons. Test balanced cohorts before adding shock labels or causal mechanisms.

Leave-one-cluster-out diagnostics rule out a single-country or single-city explanation for the pooled 2020 reversal. All 189 country deletions leave persistence worse than country mean, as do all 10,709 city deletions. However, India and China contribute 35.9% of observed cities, so deletion robustness must not be misreported as geographically balanced evidence. Add equal-country weighting and balanced-entry cohorts before interpreting the pooled effect as globally representative.

Balanced-entry and equal-country tests now show that the 2000 point-estimate reversal disappears under both corrections, while the 2020 reversal remains large. The balanced cohort contains 5,152 continuously observed cities and is more predictable, but it is a selected established-city population rather than a repair for below-threshold missingness. Equal-country metrics prevent large national city counts from determining the global average; use them alongside, not instead of, city-weighted customer-level error.

The fixed-boundary GHSL sensitivity overturns the WUP 2020 reversal: persistence MAE is 0.826 pp and the best alternative is 1.081 pp, while within-country recent/future correlation remains 0.750. This is a fixed-2025-footprint sensitivity, not validated historical geography or real-time evidence. A matched within-GHSL test now isolates boundary semantics more closely: dynamic boundaries raise pooled persistence MAE from 0.758 to 1.274 pp and reduce 2020 within-country correlation from 0.764 to 0.532, but persistence still wins 2020 in both streams. Changing polygons affects predictability but does not explain the WUP reversal.

### Endogeneity and mechanical dependence

Forecasting does not require causal exogeneity, but interpretation of coefficients and benchmark components does. Apply these controls in order:

1. Exclude the focal city's history from country and higher-level aggregates. The implemented test changes pooled country MAE by only 0.012 pp in WUP and 0.013 pp in fixed GHSL, so self-inclusion is not a material explanation.
2. Test disjoint predictor and outcome windows. Adjacent growth rates share \(P_t\) with opposite signs, so measurement error at the origin mechanically biases persistence downward. The implemented five-year-gap diagnostic weakens WUP persistence enough to lose pooled MAE and RMSE, while fixed GHSL persistence retains the best pooled scores but not every period. For the same 2020–2025 target, WUP persistence still loses without a shared 2020 endpoint; endpoint arithmetic is not a sufficient explanation.
3. Freeze size, rank and hierarchy measures strictly before the prediction window; do not use realized future rank or threshold membership. The implemented comparison computes ranks before future-outcome filtering and contrasts origin with five-year-lagged hierarchy. Neither version improves pooled MAE, and their period differences are tiny and inconsistent. Treat hierarchy as an unresolved tail-error feature, not an established independent driver.
4. Compare fixed-boundary and dynamic-boundary panels without pooling them. Fixed polygons remove changing-area arithmetic but use future boundary information; dynamic polygons confound population change with footprint change.
5. Treat spatial accessibility, built-up form and national urbanization as predictors, not causal treatments, unless a separate identification design addresses joint determination and migration sorting.

## Validation

- Use expanding or fixed rolling training windows and strictly later test periods.
- Freeze model choices before opening the final test period.
- Report MAE, RMSE, median absolute error, bias, and directional accuracy.
- Report results overall and by prespecified size, region, data-quality, and urbanization-stage strata.
- Compare errors on identical observations; coverage gains are reported separately.
- Use paired block bootstrap intervals clustered at minimum by country; add time blocks when periods overlap.
- Use leave-one-country-out and influential-city diagnostics.

### Sequential prediction-interval calibration

Point-error rankings do not establish usable uncertainty. The WUP and fixed-GHSL
workflows now construct symmetric 90% empirical error bands for each model and
forecast origin using absolute errors from strictly earlier origins only. The radius is the exact
order statistic at rank \(\lceil(n+1)(1-\alpha)\rceil\); origins with too few
calibration rows to realize that rank are not reported. Outputs report the chosen
rank, interval radius and width, city-
weighted realized coverage, equal-country realized coverage, coverage error, and the
latest calibration origin. Size-stratified tables use only prior errors in the same
size bin.

These are retrospective sequential calibration diagnostics, not guaranteed conformal
prediction intervals. Standard marginal coverage requires exchangeability; repeated
cities, country clustering, changing samples and temporal shocks violate that premise.
A band is commercially credible only if coverage remains near nominal across later
origins, size groups and equal-country summaries. Do not repair undercoverage by
recalibrating on the origin being evaluated, and do not pool WUP with GHSL to enlarge
the calibration sample.

### Model selection and the exhausted 2020 holdout

Model comparisons must separate origins used to select a specification from the origin
used to estimate its final performance. The WUP workflow now selects the lowest-MAE
candidate using pre-2020 origins and reports its 2020 MAE, rank and regret relative to
the hindsight-best 2020 model. The hindsight-best model is diagnostic only and cannot
replace the pre-2020 selection.

This calculation does **not** restore 2020 as a pristine holdout. The project inspected
2020 repeatedly while developing predictors, comparators and sensitivity tests, so the
candidate set itself reflects knowledge of that outcome. Report the new table as a
specification-search audit, not unbiased final generalization error. A defensible final
performance claim requires freezing the data contract, candidate models, metric and
weighting rule before evaluating a genuinely untouched later vintage or outcome period.
Until then, all 2020 superiority claims remain development evidence.

### Vintage limitation

A chronological holdout within WUP 2025 is **retrospective pseudo-out-of-sample validation**. It does not recreate a forecast made in an earlier year because the 2025 revision incorporates later censuses, revised methods, boundaries and national totals. Use “real-time” or “vintage-correct” only when each training input is drawn from the edition actually available at that forecast origin. Report current-revision holdouts and vintage tests separately.

The WUP 2018 F22 sensitivity is the first actual vintage test. Its 2013 and 2018
predictors and 2023 projection come from the archived 2018 edition; the scored target
comes from WUP 2025 estimates. Because the editions use different urban definitions,
it is reported only on reciprocal geographic matches and across explicit
origin-population-agreement sensitivities. It is a large-city forecast-revision test,
not a clean same-definition validation and not evidence about small cities. Match
coverage must be reported by vintage population and country because reciprocal
coordinate matching can select places whose definitions align more closely across
revisions. Forecast rankings are conditional on that matched sample unless an
explicit selection adjustment is separately identified.

Because country sample sizes vary sharply, the vintage comparison must also report
both city-weighted and equal-country estimands. Country-clustered resampling alone
does not change the city-weighted point estimate. An equal-country bootstrap instead
resamples country-level mean error differences, while leave-one-country-out estimates
test whether any single national sample determines the city-weighted result.

### Forecast-interval construction

Each five-year forecast interval requires the same city at three exact years: `origin - 5`, `origin`, and `origin + 5`. Recent growth uses only the lag and origin populations; the outcome uses origin and future populations. Density and built-up share are taken at the origin, never from the future row. Structural blanks from the 50,000 threshold remove the interval rather than being interpolated.

The default outcome filter permits WUP estimates only, so the latest eligible five-year origin is 2020 with a 2025 outcome. Using 2025–2030 or later intervals requires explicit inclusion of publisher projections and answers a different question: consistency with the UN projection, not observed forecasting accuracy. Every interval records lag, origin, and outcome observation types so the two exercises cannot be silently pooled.

Applied to five-year origins from 1980–2020, the exact-year rule yields 72,857 retrospective estimate intervals across 11,537 cities. Coverage rises from 5,638 intervals at the 1980 origin to 10,709 at 2020 because of threshold entry. Nine origin rows have missing built-up share after excluding Timerein's publisher zeros; they remain usable for population-only baselines but must drop from models requiring the built-environment covariate. This changing sample is a selection feature to report, not a nuisance to conceal with imputation.

## Threats and required attacks

| Threat | Required response |
|---|---|
| Population threshold truncation | Re-estimate around 50,000 and with balanced-entry cohorts. |
| Survivorship | Track entrants/exits and use inverse-coverage or selection sensitivity. |
| Boundary inconsistency | Flag revisions; repeat on stable-boundary subsets. |
| Endogenous rank and size | Lag predictors; distinguish prediction from causal language. |
| Large-city leverage | Leave-one-city and leave-one-country-out analyses. |
| National mechanical aggregation | Recompute national components excluding the focal city where feasible. |
| Spatial dependence | Compare country, region, distance, accessibility, border, and island specifications. |
| COVID shock | Prespecify pre-COVID, shock, and post-shock evaluations. |

The executable WUP selection ledger now separates late entry from outcome
attrition. Outcome attrition is defined as a city with population observed at the
forecast origin but missing at the required estimate outcome year. Its rate is reported
against all origin-observed cities, rather than only against complete forecast rows.
This missingness is plausibly outcome-dependent near the publication threshold, so
complete-case accuracy must be described as conditional on remaining observable.
Neither balanced cohorts nor equal weighting identify the errors of cities that
disappear. The ledger also cannot distinguish genuine decline below 50,000 from a
definition change or other publisher removal; those mechanisms require external
stable-polygon population data.

WUP F21 reports blank annual cells while a city is below 50,000. Therefore, WUP alone cannot identify behavior immediately below the threshold. Analyses must report entry cohorts and balanced samples; any regression-discontinuity-style interpretation around 50,000 is invalid without a separate source that observes both sides consistently.

## Commercial decision rule

Do not market point forecasts for individual small cities from aggregate fit statistics. A viable product requires calibrated prediction intervals, material improvement over public baselines, stable performance across geographies, and evidence that the target customer acts differently because of the forecast. Municipal financing applications may value risk bands and scenario diagnostics more than a single growth estimate.

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

The prespecified size comparison does not explain the 2020 failure: persistence loses across every size bin, and every country-clustered 95% interval excludes zero in the adverse direction. The analogous 2000 point estimates are not statistically resolved after country clustering. Pooled improvement is supported for 50–150k and above one million, but not the middle bins. Prioritize the 2015–2025 reversal and shock window before fitting flexible size interactions.

WUP temporal diagnostics show that its 2020 failure is not explained by a common slowdown. Mean growth increases from the predictor to outcome window, while recent/future Pearson correlation falls to 0.207, within-country correlation to 0.123, and the fitted persistence slope to 0.126. Direction reversals reach 29.4%. Influence and fixed-boundary tests show that this is not a single-cluster result and does not reproduce in GHSL fixed polygons. Test balanced cohorts before adding shock labels or causal mechanisms.

Leave-one-cluster-out diagnostics rule out a single-country or single-city explanation for the pooled 2020 reversal. All 189 country deletions leave persistence worse than country mean, as do all 10,709 city deletions. However, India and China contribute 35.9% of observed cities, so deletion robustness must not be misreported as geographically balanced evidence. Add equal-country weighting and balanced-entry cohorts before interpreting the pooled effect as globally representative.

The fixed-boundary GHSL sensitivity overturns the WUP 2020 reversal: persistence MAE is 0.826 pp and the best alternative is 1.081 pp, while within-country recent/future correlation remains 0.750. This is a fixed-2025-footprint sensitivity, not validated historical geography or real-time evidence. The cross-source difference identifies sensitivity to the combined source/definition package; it does not identify boundary change alone.

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

### Vintage limitation

A chronological holdout within WUP 2025 is **retrospective pseudo-out-of-sample validation**. It does not recreate a forecast made in an earlier year because the 2025 revision incorporates later censuses, revised methods, boundaries and national totals. Use “real-time” or “vintage-correct” only when each training input is drawn from the edition actually available at that forecast origin. Report current-revision holdouts and vintage tests separately.

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

WUP F21 reports blank annual cells while a city is below 50,000. Therefore, WUP alone cannot identify behavior immediately below the threshold. Analyses must report entry cohorts and balanced samples; any regression-discontinuity-style interpretation around 50,000 is invalid without a separate source that observes both sides consistently.

## Commercial decision rule

Do not market point forecasts for individual small cities from aggregate fit statistics. A viable product requires calibrated prediction intervals, material improvement over public baselines, stable performance across geographies, and evidence that the target customer acts differently because of the forecast. Municipal financing applications may value risk bands and scenario diagnostics more than a single growth estimate.

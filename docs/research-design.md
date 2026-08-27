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
4. city persistence (latest observed growth);
5. persistence plus initial log population and hierarchy position;
6. national urbanization and demographic controls;
7. spatial, border, accessibility, and shock extensions.

A complex model earns inclusion only through repeated held-out improvement over the strongest simpler baseline.

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

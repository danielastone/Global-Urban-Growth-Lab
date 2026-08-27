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

## Commercial decision rule

Do not market point forecasts for individual small cities from aggregate fit statistics. A viable product requires calibrated prediction intervals, material improvement over public baselines, stable performance across geographies, and evidence that the target customer acts differently because of the forecast. Municipal financing applications may value risk bands and scenario diagnostics more than a single growth estimate.

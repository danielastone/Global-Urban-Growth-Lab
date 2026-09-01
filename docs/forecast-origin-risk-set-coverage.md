# Forecast origin risk-set coverage policy

## Problem

A forecast evaluation can use an origin-defined threshold and still reintroduce survivorship bias if a city is admitted to the evaluation panel only when its future endpoint exists. The scoring sample then conditions on future observability even though the scientific risk set should be fixed using information available at the forecast origin.

`build_forecast_intervals` currently produces an observed-outcome scoring panel: it requires lag, origin, outcome-start, and outcome-end observations. That is appropriate for computing forecast error on rows with observable outcomes, but it is not by itself a valid denominator for claims about the origin population of cities.

## Locked rule

For coverage, attrition, survivorship, and representativeness statements, define the forecast risk set using only information available at the origin:

- the city exists at the lag year required to construct the predictor;
- the city exists at the forecast origin; and
- any origin-side eligibility rule is evaluated without using future population or future observation status.

After that risk set is fixed, classify future outcome observability separately. Missing future endpoints and disallowed future outcome types remain in the risk-set denominator.

`src/urban_growth/forecast_coverage.py` implements this separation. `origin_risk_set_outcome_coverage` returns both the city-origin risk-set rows and an origin-level coverage summary. `observed_outcome_scoring_keys` identifies the subset that can actually be scored without erasing the denominator.

## Interpretation

A low or differential `observed_outcome_share` is adverse evidence about forecast-evaluation representativeness. It must not be hidden by reporting only the observed scoring sample.

No universal acceptable coverage threshold is imposed here. A source-specific or registered analysis may define one before looking at results. Until then, headline claims must report the origin risk-set denominator, observed-outcome numerator, and exclusions rather than treating observed rows as the full cohort.

Changing a future population value, adding a future entrant, or removing a future endpoint must never change whether a city belonged to the origin risk set.

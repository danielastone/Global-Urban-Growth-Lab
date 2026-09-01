# H1 incremental information test

H1 concerns whether recent city growth contains predictive information for later city growth. A raw persistence forecast and a country-context forecast are not a nested test of that proposition: raw persistence can lose to a country mean even when recent city growth still improves prediction after country context is controlled.

The registered diagnostic in `src/urban_growth/h1_information.py` therefore compares two nested forecasts on identical city-origin rows at each rolling origin:

1. `country_loo_only`: the leave-city-out historical country mean; and
2. `country_loo_plus_recent_growth`: the same country baseline plus a coefficient on the city's recent growth deviation from its country's training-sample recent-growth mean.

The recent-growth coefficient is estimated after country demeaning and uses only training intervals whose outcomes end by the forecast origin. The test reports the coefficient, matched row counts, MAE and RMSE for both models, and the recent-minus-country error deltas. A negative delta means recent growth improves the country-context forecast.

This diagnostic does **not** retroactively redefine the preregistered universal H1. It separates two questions that were previously conflated:

- whether raw persistence is the best standalone forecast; and
- whether recent city growth adds predictive information conditional on country context.

The second question is the direct incremental-information test. Universal H1 support would still require the declared consistency conditions across origins and relevant geographic strata. A mixed sign across origins is adverse evidence even if the pooled average improves.

For WUP 2025, the runner uses the empirical-lineage correction in `wup_lineage.py`. The default observed/reference-estimate path therefore ends at the 2015 origin with a 2020 endpoint. The 2020-to-2025 interval is a CRISP projection sensitivity and is not part of this observed-outcome H1 diagnostic.

The WUP result remains retrospective revised-history evidence with changing city definitions. It is not vintage-correct and is not headline-eligible for a deployable forecasting claim.

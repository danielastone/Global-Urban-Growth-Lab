# National demographic and settlement context

## Direct national envelope

Module A now reads the registered WUP 2025 F01 `Cities`, `Towns`, `Rural`, and `Total`
sheets directly. Country-category sums must reconcile to the published total within three
persons after conversion from thousands; failure stops the build. Five-year intervals report
total growth, category growth availability, settlement shares, share changes, and a
zero-summing reallocation decomposition. Origins are restricted to a five-year grid anchored
at 1950, matching the city forecast cadence and preventing overlapping annual windows from
being treated as independent time information. These are revised-history national estimates,
not vintage-real-time observations.

An interval receives `composition_discontinuity_flag` when any settlement category appears or
disappears at an endpoint, or when any category share changes by at least 0.25 within five
years. The threshold is a prespecified audit rule, not an estimate of demographic plausibility.
All intervals remain in the `all` summaries; `stable_composition` summaries exclude flagged
intervals as a sensitivity analysis. A flag can reflect real rapid change, classification
change, or source revision and must not be interpreted as a data error without country-level
source review.

Forecast features are built separately. They contain origin settlement shares and growth or
share change from the interval completed at the origin. Realized origin-to-endpoint envelope
growth and share change are outcomes and are prohibited as forecast-origin features. Global
and regional summaries report country-equal and population-at-origin weighting separately.
They also identify whether they use all intervals or the stable-composition sensitivity sample.
The direct envelope supersedes any attempt to treat recovered Module B country-period fixed
effects as primary national demographic data; recovered effects remain diagnostic only.

## Purpose

National population and the distribution of population across cities, towns and
semi-dense areas, and rural areas are secondary forecast features. They test whether
city persistence and size effects vary with national demographic scale and settlement
structure. They are not causal treatments.

The required source is the harmonized WUP 2025 country-level Degree of Urbanisation
panel registered as un_wup_2025_country_degurb. National-definition urban shares may
be used only as a separately labeled robustness comparison because their
cross-country thresholds differ.

## Transformation contract

attach_national_context accepts normalized country-year-category populations and
forecast intervals. For focal city i, country c, and origin t, it subtracts the city's
population from both the national total and the national Cities category:

    national_population_loo(c,t,i) = national_population(c,t) - city_population(i,t)
    city_population_loo(c,t,i) = national_city_population(c,t) - city_population(i,t)

The subtraction is repeated at t minus lookback_years. National growth and changes in
settlement shares therefore contain neither the focal city's level nor its recent
growth mechanically. No value after the forecast origin is selected.

The function produces:

- leave-one-city-out national population and log population at the origin;
- annualized leave-one-city-out national population growth over the lookback window;
- origin city, town, and rural population shares;
- lookback-to-origin changes in all three shares;
- explicit provenance and availability flags.

All three shares are retained for diagnostics, but a regression with an intercept
must omit one component. The default interpretation should use rural as the reference
and include city and town shares. The town share is analytically important: an
identical urban share can describe either a deep intermediate settlement system or
concentration in a few large centres.

## Required model ladder

1. Keep the established persistence and country-mean baselines unchanged.
2. Add log national population and recent national population growth.
3. Add city and town shares, with rural omitted.
4. Test interactions with initial city size and recent city growth only after the
   additive model is evaluated out of sample.
5. Compare against country-year fixed effects in explanatory work; the national
   variables are absorbed in that specification.
6. Report matched-row forecast error changes and coverage separately.

The controls are origin-available within the WUP 2025 revised history, not
vintage-real-time information. Any real-time commercial claim still requires the
historical data revision that was available at each forecast origin.

## Edge cases

For a city-state or any record where subtracting the focal city leaves no positive
national population, the row remains in the forecast panel but the derived national
controls are missing and national_context_loo_available is false. Models requiring
these controls must report the resulting coverage loss rather than silently changing
the evaluation population.

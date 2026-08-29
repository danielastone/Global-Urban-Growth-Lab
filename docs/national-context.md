# National demographic and settlement context

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

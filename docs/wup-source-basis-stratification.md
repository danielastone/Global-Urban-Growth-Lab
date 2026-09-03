# WUP source-basis stratification contract

WUP 2025 M01 documents the latest population input used by the underlying GHSL
population grid for each country or area. It records the input year, census/register/estimate
process type and administrative granularity. It is a country-level construction-input record,
not a city-year observation register.

Accordingly, the #132 analysis attaches M01 metadata to every evaluated WUP city-origin row
but records `city_direct_observation_status = unresolved` and
`city_source_resolution = country_proxy_only`. No M01 census label is converted into a claim
that a particular WUP city value is a direct census count.

## Recency states

Recency is measured against the forecast origin:

- `post_origin_input`: the M01 input year is later than the historical origin, showing that
  the current WUP revision backcasts that origin using information unavailable then;
- `recent_direct_input`: census/register input is zero to ten years before the origin;
- `stale_direct_input`: census/register input is more than ten years before the origin;
- `estimate_input`: a non-direct estimate input predates the origin; and
- `unresolved`: required M01 fields are unavailable.

The signed year distance is retained. A later input is not mislabeled as a negative number of
“years since census.”

## Estimation

The locked #133 nested comparison is repeated by origin within three documentary
stratifications: recency state, source process type and input administrative level. The
baseline is same-origin, same-country leave-city-out peer growth; the augmented model adds
the focal city's deviation from that signal. Both are scored on identical rows.

Each stratum reports rows, countries, population and population coverage. Row-weighted and
equal-country fits are separate. A stratum is not backfilled from later data: if no matching
prior-origin training rows exist, it is retained with
`evaluation_status = insufficient_prior_stratum_training` and null estimates.

This is a measurement-lineage sensitivity. It cannot identify census age as a causal
mechanism, and it cannot replace validation against direct locality counts.

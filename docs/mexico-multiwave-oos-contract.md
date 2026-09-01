# Mexico multiwave locality OOS contract

## Decision

Mexico can potentially supply the first national-census-family, multi-origin persistence test without future-boundary leakage, but only if each adjacent locality transition is independently concorded and audited.

INEGI SCITEL exposes locality-level population for the 1990 census, 1995 population count, 2000 census, 2005 population count, 2010 census, and 2020 census. The 1995 and 2005 products are national population counts with locality-level geographic breakdown; they are not silently treated as identical to censuses. Every census/count transition therefore requires an explicit `methodology_comparable` decision before it may enter a growth predictor or outcome.

## Why the 1995 and 2005 counts matter

A decennial-only 2000–2010–2020 panel yields only one usable rolling forecast origin once a prior growth interval is required. Adding the official 1995 and 2005 locality counts creates candidate five-year chains such as:

- 1990–1995 history → 1995–2000 outcome;
- 1995–2000 history → 2000–2005 outcome;
- 2000–2005 history → 2005–2010 outcome.

The 2010–2020 transition may also be evaluated, but its ten-year horizon is not automatically pooled with five-year outcomes. Horizon-specific results must remain separate unless an explicit annualized-growth estimand and pooling rule are registered.

## No-future-boundary rule

Each adjacent transition is evaluated using only official relationship, locality-history, and vintage-geometry evidence available no later than that transition endpoint. A 2005 or 2010 geographic relationship cannot be used to redefine the 1990–1995 or 1995–2000 predictor geography.

For a forecast row at origin `t`:

1. the immediately prior transition ending at `t` must independently pass the concordance and methodology rules;
2. the outcome transition beginning at `t` must independently pass;
3. later geography cannot repair either transition;
4. a failed prior transition makes the forecast row ineligible even when the outcome transition is clean.

This is the central protection against using future geographic knowledge to manufacture persistence.

## Transition acceptance

Accepted statuses remain:

- `stable_geometry`;
- `official_crosswalk`;
- `harmonized_common_geography`.

One-to-one matches require an official relationship and at least 99.5% polygon overlap against both endpoint units. Harmonized split/merge/transfer cases require all official components, complete population aggregation, no double counting, and the same polygon-union overlap rule. Name equality, fuzzy matching, or coordinate proximity may generate candidates but cannot establish acceptance.

Each accepted transition additionally requires `methodology_comparable = true`. This field is deliberately separate from geographic concordance because a geographically stable locality can still be unsuitable for a population-growth comparison if census/count concepts or coverage differ materially.

## Coverage gate

Coverage is calculated before unresolved records are removed. For every transition and the registered 25,000–100,000 origin cohort, report both:

- locality-count coverage;
- origin-population-weighted coverage.

The existing proposed Mexico gate remains at least 85% count coverage and at least 90% population coverage, with every detected split, merger, annexation, or municipal transfer resolved or explicitly excluded. These thresholds remain provisional until the exact national files are acquired and the first full transition audit is run.

## Forecast use

`src/urban_growth/mexico_concordance.py` converts accepted adjacent transitions into forecast rows only when both the prior-history and current-outcome transitions pass. The resulting rows expose `recent_growth`, `future_growth`, `period_start`, `period_end`, `forecast_horizon_years`, and source-specific `growth_eligible` for the common persistence benchmark layer.

Source-specific transition eligibility is not sufficient for either a headline claim or a deployable forecast. The builder therefore fails both statuses closed:

- `headline_eligible = false` with `common_city_data_fitness_not_applied` until the row has been evaluated under the common City Data Fitness Standard, including truncation/survivorship and adverse-evidence fields;
- `forecast_deployable_at_origin = false` with `point_in_time_availability_not_applied` until explicit predictor/concordance availability dates have passed the point-in-time gate.

A Mexico row may therefore be suitable for a retrospective source-specific growth benchmark while still being ineligible for headline or deployable classification. Downstream code must not infer those stronger statuses from `forecast_interval_eligible` or `growth_eligible`.

No empirical Mexico persistence result is registered by this contract. Exact ITER/SCITEL files, official equivalence records, vintage Marco Geoestadístico layers, retrieval dates, URLs, and hashes must be acquired and registered first.

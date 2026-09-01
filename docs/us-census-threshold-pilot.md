# U.S. Census place threshold pilot

## Purpose and scope

This pilot validates the census-threshold pipeline with official U.S. decennial place
counts. It does **not** satisfy the specification's Global South feasibility gate and
does not replace the Mexico, Brazil, South Africa, or Ghana pilots. U.S. place
identifiers and Census relationship files make this a comparatively favorable test of
the implementation rather than a demanding test of international harmonization.

The first registered interval is 2010–2020. The origin denominator contains **every**
2010 place with 25,000–100,000 residents before any relationship, overlap, or endpoint
filter is applied. Cohort membership is defined only from the 2010 origin population.
The 2020 population is an outcome and cannot add a future entrant, remove a later
decliner, or otherwise redefine the origin risk set.

A place crosses the WUP observation threshold when its directly enumerated population
is below 50,000 in 2010 and at least 50,000 in 2020. Crossing is interval-censored in
the open interval `(2010, 2020)`; the code does not invent a point crossing year.

## Official inputs

| Input | Official field | Role |
|---|---|---|
| 2010 Decennial Census SF1 place population | `P001001` | Origin population and denominator membership |
| 2020 Decennial Census PL 94-171 place population | `P1_001N` | Endpoint outcome |
| 2020-place to 2010-place national relationship file | Place GEOIDs, endpoint land areas, intersection land area | Post-membership concordance classification |

Population is retrieved for the 50 states and District of Columbia. Puerto Rico is
outside this initial U.S. pilot. The relationship file is the official pipe-delimited
national file at
`https://www2.census.gov/geo/docs/maps-data/data/rel2020/place/tab20_place20_place10_natl.txt`.

## Origin denominator before concordance

`urban_growth.adapters.us_census.build_us_place_origin_denominator` is the canonical
U.S. pilot denominator constructor. It first fixes the 25,000–100,000 cohort from 2010
population, then attaches relationship evidence and endpoint population.

Every origin place remains represented with:

- `cohort_defined_at_origin = true`;
- `cohort_population_basis = population_origin`;
- `cohort_uses_endpoint_population = false`;
- `concordance_resolved`;
- `endpoint_population_observed`;
- `analysis_eligible`;
- a controlled `concordance_exclusion_reason` when unresolved.

This prevents non-one-to-one relationships, boundary changes, missing relationship
evidence, or missing endpoint data from silently disappearing before coverage is
measured. The analysis cohort is a subset of this denominator; it is not the
denominator itself.

`us_place_concordance_coverage` reports both count and origin-population coverage for
resolved concordances and final analysis eligibility. No production minimum coverage
threshold is registered yet. Coverage must be reported before any threshold-crossing
result is promoted.

## Comparable-geography rule

A repeated GEOID alone is not treated as proof of stable geography. A place is resolved
only when its relationship is one-to-one in both directions and its intersection land
area is at least 99.5% of both the 2010 and 2020 place land areas. A changed GEOID can
enter as an `official_crosswalk` when it passes those same rules.

Places that fail these rules remain in the origin denominator with
`geography_status = unresolved`; they are excluded only from the resolved analysis
sample. This distinction is essential because geography instability may correlate with
growth and threshold crossing.

The land-overlap rule is a conservative feasibility screen. It is not proof that
population was enumerated on perfectly identical geography, and the retained overlap
ratios remain in the resolved output for sensitivity analysis.

## Origin-defined cohort rule

`urban_growth.census_threshold.origin_defined_threshold_cohort` remains the generic
constructor for already comparable boundary cohorts. For the U.S. pilot, however,
comparability cannot be allowed to define the denominator. The adapter-specific
`build_us_place_origin_denominator` therefore precedes the generic resolved-cohort
logic.

A locality with 20,000 people at origin and 70,000 at the endpoint remains outside a
25,000–100,000 origin cohort, while a locality with 80,000 at origin and 30,000 at the
endpoint remains inside the denominator even if its geography later proves unresolved.
Endpoint growth, threshold crossing, concordance success, and later survival therefore
cannot determine denominator membership.

## City Data Fitness gate

Only the resolved analysis cohort is passed through `urban_growth.census_fitness` before
headline analysis. The adapter translates the accepted boundary evidence into the
common City Data Fitness vocabulary and then calls the repository-wide evaluator.

For this pilot:

- direct 2010 and 2020 decennial counts are temporally comparable for the registered
  total-population growth use;
- `stable` and `official_crosswalk` geography states are accepted because both have
  already passed the one-to-one and 99.5% land-overlap screen;
- truncation and survivorship exposure are labeled `low`, not `none`, because the
  registered analysis is conditional on the explicit 25,000–100,000 origin cohort;
- the cohort is not spatial/network eligible because coordinates and network geography
  are not validated by this pilot;
- the headline sample is written separately and can only be produced through the
  common `headline_eligible` gate.

The `low` truncation/survivorship label does not override the new concordance-coverage
report. If unresolved places are material, the headline interpretation must remain
qualified even when resolved rows pass row-level fitness checks.

## Acquisition and execution

Request a Census API key and export it in the local shell without writing it to the
repository:

```bash
export CENSUS_API_KEY
uv run --locked python scripts/fetch_us_census_place_pilot.py
uv run --locked python scripts/run_us_census_threshold_pilot.py
```

The acquisition script saves untouched API responses and the official relationship
file under `data/raw/`. Those inputs must be inventoried in `data/manifest.csv` with
their retrieval date, exact URL, and SHA-256 hash before an empirical result is
registered.

The runner writes four outputs under `outputs/`:

- the complete origin-defined denominator;
- the resolved, fitness-annotated cohort;
- the strict headline-eligible subset;
- the summary containing count and origin-population concordance coverage.

Generated outputs remain outside Git unless explicitly registered through the result
manifest process.

## Current status and decision rule

The adapter, acquisition script, origin-first denominator, concordance coverage summary,
resolved cohort builder, City Data Fitness application, and synthetic contract tests are
implemented. The empirical run is blocked until a Census API key is available; no
modeled or intercensal estimate will be substituted for the two decennial counts.

The summary deliberately writes `gate_g2_satisfied = false` and
`coverage_threshold_registered = false`. Successful execution shows that the common
threshold-audit and fitness-gating code works against an official, well-documented
national system while exposing any concordance attrition against the full origin cohort.
It does not establish that comparable multiwave locality data are available in the
countries central to the global claim, nor does it authorize a headline if concordance
coverage is poor. The next feasibility decision therefore remains a Mexico or Brazil
pilot.

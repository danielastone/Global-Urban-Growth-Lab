# U.S. Census place threshold pilot

## Purpose and scope

This pilot validates the census-threshold pipeline with official U.S. decennial place
counts. It does **not** satisfy the specification's Global South feasibility gate and
does not replace the Mexico, Brazil, South Africa, or Ghana pilots. U.S. place
identifiers and Census relationship files make this a comparatively favorable test of
the implementation rather than a demanding test of international harmonization.

The first registered interval is 2010–2020. The origin cohort contains places with
25,000–100,000 residents in 2010. A place crosses the WUP observation threshold when
its directly enumerated population is below 50,000 in 2010 and at least 50,000 in
2020. Crossing is interval-censored in the open interval `(2010, 2020)`; the code does
not invent a point crossing year.

## Official inputs

| Input | Official field | Role |
|---|---|---|
| 2010 Decennial Census SF1 place population | `P001001` | Origin population |
| 2020 Decennial Census PL 94-171 place population | `P1_001N` | Endpoint population |
| 2020-place to 2010-place national relationship file | Place GEOIDs, endpoint land areas, intersection land area | Comparable-geography screen |

Population is retrieved for the 50 states and District of Columbia. Puerto Rico is
outside this initial U.S. pilot. The relationship file is the official pipe-delimited
national file at
`https://www2.census.gov/geo/docs/maps-data/data/rel2020/place/tab20_place20_place10_natl.txt`.

## Comparable-geography rule

A repeated GEOID alone is not treated as proof of stable geography. The registered
cohort keeps only relationships that are one-to-one in both directions and whose
intersection land area is at least 99.5% of both the 2010 and 2020 place land areas.
A changed GEOID can enter as an `official_crosswalk` when it passes those same rules.
All other relationships are excluded rather than interpreted as demographic change.

This land-overlap rule is a conservative feasibility screen. It is not proof that
population was enumerated on perfectly identical geography, and the retained overlap
ratios remain in the output for sensitivity analysis.

## City Data Fitness gate

The registered cohort is passed through `urban_growth.census_fitness` before any
headline analysis. The adapter translates the existing boundary evidence into the
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

This fitness decision is specific to the registered 50,000-threshold analysis. It must
not be generalized to arbitrary U.S. place level comparisons, spatial models, or
samples outside the 25,000–100,000 origin range.

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
registered. The fitness-annotated cohort, strict headline sample, and summary are
written under `outputs/` and remain outside Git.

## Current status and decision rule

The adapter, acquisition script, cohort builder, City Data Fitness application, and
synthetic contract tests are implemented. The empirical run is blocked until a Census
API key is available; no modeled or intercensal estimate will be substituted for the
two decennial counts.

The summary deliberately writes `gate_g2_satisfied = false`. Successful execution
shows that the common threshold-audit and fitness-gating code works against an
official, well-documented national system. It does not establish that comparable
multiwave locality data are available in the countries central to the global claim.
The next feasibility decision therefore remains a Mexico or Brazil pilot.

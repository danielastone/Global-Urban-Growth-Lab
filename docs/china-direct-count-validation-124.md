# China direct-count qualification for issue #124

China is highly relevant to #124 because it contributes a large share of the WUP city
sample. It does not currently supply a qualified direct-locality validation panel.

## Why three national censuses are insufficient

The National Bureau of Statistics publishes the 2000, 2010, and 2020 national population
censuses. These are direct enumerations, but three waves yield only one recent-to-future
forecast origin: 2000–2010 growth predicting 2010–2020 growth. The repository's #124 gate
requires at least two origins rather than estimating a general persistence relationship from
one national decade pair.

More importantly, the published county-level units include counties, county-level cities,
and urban districts. These are administrative territories, not stable settlement footprints.
Prefecture-level “cities” can contain extensive rural hinterlands. District annexations,
splits, mergers, and code changes alter both population and land area independently of
demographic growth. Matching unchanged names or administrative codes does not resolve this.

## Why annual city series do not solve it

China's statistical and urban-construction yearbooks contain long annual series, but the
fields can refer to administrative-area population, urban districts, built-up areas,
permanent residents, or hukou population. They are not interchangeable direct locality
counts. Combining them would manufacture apparent growth from definition changes.

NBS statistical division and urban-rural division codes distinguish main-city areas,
urban-rural fringes, town centres, and rural areas for each vintage. They are useful inputs
for a future geographic audit, but they do not themselves provide population counts or a
population-weighted crosswave concordance.

## Machine-readable decision

Run:

```bash
uv run --locked python scripts/run_construction_smoothing_124.py --pilot china
```

The runner writes `china_source_qualification.csv` and
`china_benchmark_status.csv`. The current decision is
`unresolved_no_stable_locality_multiwave_population_concordance`, with
`benchmark_estimable=false` and `h1_independent_confirmation=false`.

A 2000–2020 county-level exercise is allowed only as an administrative-unit sensitivity.
It cannot close #124 or be described as direct city validation. A qualifying path requires
at least four direct-enumeration waves, origin-specific settlement footprints, consistent
permanent-resident population concepts, and official population-weighted concordances for
every adjacent transition. Until those inputs exist, China is not a shortcut around the
U.S. and India constraints.

Official source entry points:

- NBS census data: https://www.stats.gov.cn/english/Statisticaldata/CensusData/
- Seventh census release: https://www.stats.gov.cn/english/PressRelease/202105/t20210510_1817185.html
- NBS statistical standards: https://www.stats.gov.cn/sj/tjbz/

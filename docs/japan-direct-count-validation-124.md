# Japan direct-count qualification for issue #124

Japan is the first reviewed country to complete the direct-count/GHS-POP benchmark.
The source qualification and matched result are now implemented.

## Recommended unit: Densely Inhabited Districts

The Statistics Bureau defines Densely Inhabited Districts (DIDs) from Population Census
small-area data and has designated them in every census since 1960. DIDs are census-defined
urban areas rather than whole municipalities. Official census population and vintage geography
for 2000, 2005, 2010, 2015, and 2020 provide three possible recent-to-future origins.

That does not authorize a naive DID-code join. DID boundaries can expand, contract, split, or
merge. The implementation therefore withholds empirical qualification until the official inputs
are registered, each origin denominator is constructed before later concordance, and a geometry
overlap audit classifies stable one-to-one relationships, splits, mergers, births, and disappearances.
Every unresolved origin DID must remain in the coverage denominator.

## Rejected shortcuts

Municipality census tables are useful administrative-area sensitivities but municipalities can
contain multiple settlements and rural territory. Japan's official tables also publish prior-census
population readjusted to later municipal boundaries. Those adjacent comparisons are valuable for
transition checks, but chaining them into a historical panel on a later municipality universe would
condition earlier membership on future mergers and boundaries.

Small-area grid data could support a fixed-footprint sensitivity, but grid cells are not official
localities. Aggregating them directly to a future GHSL footprint would reproduce the future-membership
problem rather than test it.

## Implemented acquisition sequence

1. Acquire and hash official DID population tables and vintage polygons for 2000–2020.
2. Define the eligible DID population cohort independently at each forecast origin.
3. Overlay only the lag, origin, and outcome vintages needed at that origin; do not use 2020
   membership to construct earlier risk sets.
4. Require one-to-one overlap thresholds for the primary sample and retain all other origin DIDs
   as unresolved denominator rows.
5. Match GHSL fixed and dynamic population to the accepted DID-period rows without using future
   outcomes for membership.
6. Run the registered #124 coefficient, MAE/RMSE, sign-reversal, and curvature comparisons.

Run the current qualification gate with:

```bash
uv run --locked python scripts/run_construction_smoothing_124.py --pilot japan
```

It writes `japan_source_qualification.csv` and `japan_benchmark_status.csv`. The DID source is now
qualified after registered acquisition, origin-denominator construction, and geometry-overlap audit.
Run `scripts/run_japan_ghsl_match_124.py` for the matched benchmark; results and limitations are in
`docs/japan-ghsl-match-124-result.md`.

Official source entry points:

- Population Census: https://www.stat.go.jp/english/data/kokusei/
- DID definition: https://www.stat.go.jp/english/data/chiri/did/1-1.html
- e-Stat official data portal: https://www.e-stat.go.jp/en/

# WUP H1 source-basis stratification — 2026-09-03

## Scope and non-identification

This result addresses issue #132 using WUP 2025 M01, which documents the latest
country-level population input used by the GHSL population grid underlying WUP. M01 does
not identify direct observations for individual cities. Consequently, all 56,510 evaluated
city-origin rows have resolved country-input metadata and
`city_direct_observation_status = unresolved`.

The result is a measurement-lineage sensitivity, not proof that census age causes differences
in predictive performance and not a substitute for direct locality-count validation.

## Empirical run and durable lineage

- GitHub Actions run: `33707807331`
- producing commit: `d57a9173c6f2f1df6321c67ba87c2b016eef78ba`
- workflow: `.github/workflows/wup-source-basis-h1.yml`
- artifact ID: `9875860058`
- artifact digest: `sha256:c66c1e0ed3e2058d2b28b50d6ae3253550e39fb05fb0f0ef13633f1b0a7e4ddb`
- artifact expiry: 2026-12-02
- durable package: `wup-h1-source-basis-2026-09-03`

The complete row classification is retained as a deterministic gzip CSV. Its uncompressed
artifact-member SHA-256 is
`25ef713bd022b5deaa54fbaef74b77f5376b73dc8a47f4a946273a605defd1e8`;
the registry records the committed compressed-file hash separately.

## Coverage and source construction

M01 classifies 50,543 evaluated rows under census inputs, 3,688 under estimates and 2,279
under population registers. These are country-input labels, not city-count labels.

| Origin | Post-origin input | Estimate input | Recent direct input | Stale direct input |
|---:|---:|---:|---:|---:|
| 1985 | 6,147 | 0 | 0 | 0 |
| 1990 | 6,744 | 0 | 0 | 0 |
| 1995 | 7,280 | 0 | 0 | 0 |
| 2000 | 8,051 | 0 | 0 | 0 |
| 2005 | 8,540 | 80 | 202 | 0 |
| 2010 | 3,623 | 525 | 5,328 | 0 |
| 2015 | 0 | 727 | 9,125 | 138 |

Every evaluated row through the 2000 origin uses an M01 input dated after that origin. This
directly confirms that the current-revision WUP history is backcast using later information; it
cannot represent a historical real-time forecast information set.

## H1 stratified result

Within broad M01 process types, adding focal-city growth deviation improves MAE for census,
register and estimate strata at all evaluable origins under both weighting schemes. Two RMSE
exceptions remain: row-weighted census inputs in 2000 and equal-country register inputs in
2015.

The recency split exposes a more consequential instability:

- At the 2010 origin, the recent-direct-input stratum covers 5,328 cities, 88 countries and
  59.6% of evaluated population.
- Its row-weighted fit remains favorable: beta 0.199, with MAE and RMSE improvements of
  approximately 0.109 and 0.104 percentage points.
- Its equal-country fit reverses: beta -0.559, with MAE worsening by 0.716 percentage points
  and RMSE worsening by 1.011 percentage points.
- Only 202 prior rows occupy that same recency state, so this reversal is an instability signal,
  not a precise estimate of a census-recency mechanism.
- By 2015, recent-direct inputs cover 9,125 cities and 91.7% of population; both row-weighted
  and equal-country estimates are positive and improve both losses.

Six origin/stratum/weighting cells are retained with
`insufficient_prior_stratum_training` rather than silently borrowing later information: the
2005 estimate and recent-direct strata, and the 2015 stale-direct stratum, each under two
weighting schemes.

Administrative-level splits contain additional reversals, especially in small or
country-concentrated strata. They are reported as heterogeneity diagnostics rather than an
ordered measure of source quality.

## Conclusion

H1 survives most broad source-process splits, but it is not stable enough to be promoted to a
universal or headline claim. Equal-country performance reverses in the 2010 recent-direct
stratum, early origins are entirely backcast from later population inputs, and city-specific
direct-count lineage remains unresolved. The direct census/admin locality evidence required by
issue #124 remains the external validation gate.


# WUP H1 incremental recent-growth result — 2026-09-01

## Question

Does a city's recent growth add predictive information beyond leave-city-out country context, rather than merely asking whether raw persistence beats a country mean?

## Data lineage

The run uses WUP 2025 DEGURBA city tables F21, F25, F30, and F34 acquired directly from UN DESA in GitHub Actions run `33559560861`. Source SHA256 values are registered in `results/wup_h1_incremental_source_sha256.txt`.

The empirical-lineage gate treats 1975–2020 as GHS-WUP-POP reference estimates and post-2020 values as CRISP-generated projection values. Therefore the observed/reference-estimate diagnostic ends at the 2015 origin with a 2020 endpoint. The 2020→2025 interval is not part of this result.

## Nested test

For each origin, the comparison is:

1. leave-city-out country-context forecast; versus
2. the identical country-context forecast plus the city's recent-growth deviation from its country's historical recent-growth mean.

The recent-growth coefficient is estimated only from training outcomes ending by the forecast origin after country demeaning. Both models are scored on identical test rows.

## Result

| Origin | Cities | Within-country recent-growth beta | MAE improvement | RMSE improvement | Improves both? |
|---:|---:|---:|---:|---:|:---:|
| 1985 | 6,147 | 0.454 | 24.7% | 17.0% | Yes |
| 1990 | 6,744 | 0.499 | 11.9% | 11.7% | Yes |
| 1995 | 7,280 | 0.502 | 25.9% | 23.0% | Yes |
| 2000 | 8,051 | 0.539 | 7.8% | -0.7% | No |
| 2005 | 8,822 | 0.453 | 24.9% | 16.1% | Yes |
| 2010 | 9,476 | 0.463 | 21.9% | 11.5% | Yes |
| 2015 | 9,990 | 0.463 | 22.7% | 17.0% | Yes |

Recent growth improves MAE at all seven observed origins and RMSE at six of seven. The estimated within-country recent-growth coefficient is positive and tightly ranged from 0.453 to 0.539 across origins.

## Interpretation

This materially weakens the earlier interpretation that WUP evidence shows recent growth becoming uninformative when a country mean wins. The correct nested test shows that recent growth continues to add information conditional on country context throughout the observed/reference-estimate sample.

However, the preregistered universal H1 remains too strong if it requires recent growth to improve both MAE and RMSE at every origin: the 2000 origin improves MAE but worsens RMSE by about 0.7%. The defensible conclusion is therefore:

> Recent growth is a robust incremental predictor of typical city-growth error beyond country context in revised-history WUP data, but its improvement is not universal across all loss functions and origins.

This is still a retrospective current-revision WUP result with changing city definitions and no vintage-correct information set. `headline_eligible` remains false.

The machine-readable result is `results/wup_h1_incremental_recent_growth_by_origin.csv`.

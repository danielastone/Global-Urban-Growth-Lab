# WUP contemporaneous-country recent-growth diagnostic

## Question

Does a city's own recent growth outperform the contemporaneous recent-growth state of its other same-country cities at the same forecast origin?

This diagnostic addresses red-team Finding 5. The comparator is fully origin-available and leave-city-out. Singleton-country observations fall back to the contemporaneous global leave-city-out mean. It does not use future outcomes.

## Empirical run

- GitHub Actions run: `33571092887`
- producing head commit: `29da2ff04463456bc716f40649c8ef4e45319b49`
- artifact: `wup-contemporaneous-country-diagnostic`, artifact ID `9824957096`
- artifact digest: `sha256:00bfe9530c43337871b8325fa4fc2e3fc39db8934083d4b9e38bf55af9a3612b`
- observed/reference-estimate scoring origins: 1985–2015
- 2020->2025 CRISP outcome excluded

Source workbook SHA-256 values match the registered WUP city inputs:

- F21 population: `3a96030d87aec6c1c50f658d5321067d6345e1ab936c5d2854524f972caa75c0`
- F25 area: `1174b1d46344a14c6d92d5a85e8b852cb789cf4d67835c2ff96c1634450af25f`
- F30 built-up area per capita: `942a9d74e66949cd8eb818fa208b9402bbd5225a1dbce7f98c3101f9904ba34f`
- F34 density: `aff1240a0db72de6adabb5fb8a734df2d9be3159f94886c18ff61d5eaea1f0b0`

## Point estimates

| Origin | Persistence MAE | Contemporaneous-country MAE | Persistence minus peer MAE | Persistence RMSE | Peer RMSE | Persistence minus peer RMSE |
|---:|---:|---:|---:|---:|---:|---:|
| 1985 | 1.002 pp | 1.406 pp | -0.404 pp | 1.982 pp | 2.201 pp | -0.219 pp |
| 1990 | 1.616 pp | 1.759 pp | -0.143 pp | 2.512 pp | 2.552 pp | -0.040 pp |
| 1995 | 1.239 pp | 1.815 pp | -0.576 pp | 2.172 pp | 2.620 pp | -0.447 pp |
| 2000 | 1.598 pp | 1.346 pp | **+0.252 pp** | 2.741 pp | 1.944 pp | **+0.797 pp** |
| 2005 | 0.989 pp | 1.242 pp | -0.254 pp | 1.850 pp | 1.911 pp | -0.061 pp |
| 2010 | 1.157 pp | 1.337 pp | -0.180 pp | 2.156 pp | 2.055 pp | **+0.100 pp** |
| 2015 | 1.356 pp | 1.690 pp | -0.334 pp | 2.304 pp | 2.493 pp | -0.189 pp |

Persistence has lower MAE at six of seven origins. The exception is 2000, where contemporaneous same-country peer growth improves MAE by about 0.252 percentage points and RMSE by about 0.797 percentage points. At 2010 persistence retains the lower MAE but the contemporaneous comparator has the lower RMSE.

## Country-cluster uncertainty

The one-way country-cluster bootstrap uses 2,000 repetitions and seed `20260827`.

| Origin | MAE difference: persistence - peer | 95% country-cluster CI | P(persistence better) |
|---:|---:|---:|---:|
| 1985 | -0.404 pp | [-0.503, -0.303] pp | 1.000 |
| 1990 | -0.143 pp | [-0.427, +0.158] pp | 0.738 |
| 1995 | -0.576 pp | [-1.080, -0.101] pp | 0.994 |
| 2000 | +0.252 pp | [-0.132, +0.681] pp | 0.381 |
| 2005 | -0.254 pp | [-0.339, -0.192] pp | 1.000 |
| 2010 | -0.180 pp | [-0.281, -0.092] pp | 1.000 |
| 2015 | -0.334 pp | [-0.484, -0.183] pp | 1.000 |

The 2000 point estimate is consistent with a regime in which current country peer growth is more useful than own-city persistence, but its country-cluster MAE interval crosses zero. It is therefore evidence of period sensitivity, not a definitive estimate of a national-convergence mechanism.

Across all seven observed origins, the two-way country/origin bootstrap gives an average MAE difference of -0.228 pp, 95% CI [-0.447, -0.018] pp, with probability persistence is better 0.979. Thus the new comparator does not overturn persistence as the stronger average predictor in revised-history WUP; it does reveal an important period-specific failure that the historical-mean comparator could not isolate.

## Interpretation

Finding 5 is confirmed as a missing instrument, but its empirical addition yields a more nuanced result than a simple national-convergence story:

- own-city recent growth usually beats the contemporaneous country peer state;
- the 2000 origin is a clear point-estimate reversal on both MAE and RMSE;
- the 2000 MAE advantage of the peer comparator is not statistically decisive under country-cluster resampling;
- 2010 also shows a tail-error advantage for the contemporaneous comparator despite persistence winning MAE.

The correct headline remains that recent growth contains substantial city-specific predictive information beyond aggregate country context, while regime changes can make contemporaneous national/country information especially valuable.

Exact output SHA-256 values:

- metrics CSV: `6a45bd93a1d53019d772adb4027cc327aa965524badbd5b6afeeaf76d61b3123`
- country-cluster bootstrap CSV: `efd77d62b64c479d0238fc561e3a9cba6e3a1fe53cecf42a0c6b972a83fa18c9`
- country/origin bootstrap CSV: `e68bc31fc04d04acd0f54ced20bcd9027e37412da04d36df9db513cbe53b9836`

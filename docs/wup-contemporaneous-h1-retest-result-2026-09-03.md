# WUP contemporaneous-country H1 re-test — 2026-09-03

## Design

This is the separate result lineage required by issue #133. For each origin, the primary
baseline is the same-origin recent growth of other cities in the focal city's country.
The nested model adds the focal city's deviation from that leave-city-out peer signal.
Singleton countries use a same-origin global leave-city-out fallback. No future outcome
enters either predictor.

Coefficients use only training outcomes ending by the forecast origin. All four models
are scored on identical rows. Results are reported independently by origin under ordinary
row weighting and equal-country weighting; no pooled winner or later-origin information
selects a model.

## Empirical run and durable lineage

- GitHub Actions run: `33706481000`
- producing commit: `0b0f72d799d96a15e93f7ff1a1fd6c1f2116d906`
- workflow: `.github/workflows/wup-contemporaneous-country.yml`
- artifact ID: `9875394121`
- artifact digest: `sha256:68d8af67527ef9120fab4dbce4e77984edb4c8c76a6a283e52978e9dfa4c9d9d`
- artifact expiry: 2026-12-02
- durable package: `wup-contemporaneous-h1-retest-2026-09-03`

The Actions artifact is transient operational metadata. The retained hierarchy CSV and
its individual hash are registered in the durable evidence tables.

## Primary nested result

The percentages below are improvements from adding the focal-city deviation to the
contemporaneous-country baseline. Positive values mean lower error.

| Origin | Cities | Countries | Row beta | Row MAE | Row RMSE | Equal-country beta | Equal-country MAE | Equal-country RMSE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1985 | 6,147 | 174 | 0.479 | 26.8% | 20.0% | 0.519 | 33.0% | 31.9% |
| 1990 | 6,744 | 177 | 0.531 | 13.0% | 11.8% | 0.527 | 15.3% | 2.5% |
| 1995 | 7,280 | 179 | 0.527 | 25.4% | 23.5% | 0.499 | 15.3% | 7.7% |
| 2000 | 8,051 | 181 | 0.569 | 4.8% | **-3.2%** | 0.474 | 19.5% | 18.4% |
| 2005 | 8,822 | 182 | 0.479 | 20.5% | 14.4% | 0.468 | 18.5% | 9.6% |
| 2010 | 9,476 | 186 | 0.486 | 16.1% | 9.3% | 0.471 | 20.9% | 11.3% |
| 2015 | 9,990 | 186 | 0.481 | 16.1% | 12.8% | 0.475 | 14.2% | 9.4% |

The focal-city deviation improves MAE at all seven origins under both weighting schemes.
It improves RMSE at all seven origins under equal-country weighting and six of seven under
row weighting. The exception is 2000, when row-weighted RMSE worsens by 3.2%.

## Full-hierarchy reversals

The augmented contemporaneous model is not universally best. Under row weighting, the
historical augmented model has the lowest MAE in 1990, 1995 and 2000; historical models
also have the lowest RMSE in 1995, 2000 and 2005. Under equal-country weighting, the
contemporaneous augmented model wins MAE at every origin, but historical models win RMSE
in 1990, 1995 and 2015.

## Interpretation

The re-test supports city-specific incremental persistence beyond a contemporaneous
national/common city-growth signal. Country balancing strengthens that conclusion rather
than revealing domination by countries with many cities. It does not support a universal
model-ranking claim: the 2000 row-weighted tail-error reversal remains, and historical
country-context variants win several origin/loss combinations.

This remains a retrospective current-revision WUP result. WUP source construction,
changing city definitions and the absence of vintage-correct information prevent headline
eligibility. Direct census/admin locality validation and source-basis stratification remain
separate empirical gates.


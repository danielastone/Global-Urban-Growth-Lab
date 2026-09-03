# Japan direct-count/GHS-POP benchmark — issue 124

## Decision

The Japan result does not support the construction-smoothing explanation tested in issue #124.
GHS-POP persistence is not consistently stronger than persistence in direct census DID counts on
the same locality-period rows. Direct counts themselves show positive persistence value in every
forecast-origin period, but this is evidence for a Japan DID sample—not universal confirmation of
H1 or a causal claim.

## Inputs and matching

- Direct source: official MLIT A16 Population Census DID polygons and counts, 2000–2020, from 97
  SHA-256-registered archives.
- GHSL source: GHS-POP R2023A at 100 m for the same five epochs, from 40 SHA-256-registered tiles.
- Cohort: 25,000–100,000 direct-count population at each forecast origin, fixed before concordance.
- Dynamic identity: one-to-one adjacent DID transitions with at least 50% mutual area overlap.
- Strict stability: one-to-one transitions with at least 99.5% mutual overlap; this is the primary
  geographic-validity sample.
- Fixed GHS-POP treatment: all three raster epochs aggregated inside the origin DID polygon.
- Dynamic GHS-POP treatment: each raster epoch aggregated inside its contemporaneous matched DID.
- Raster inclusion: 100 m cell centres inside the target polygon. Missing raster support is retained
  as ineligible in the origin denominator, never converted to zero.

The direct denominator contains 1,034 forecast-origin DIDs across 2005, 2010, and 2015. Three-wave
coverage is 874 (84.5%) under dynamic identity and 74 (7.2%) under strict stability. The latter is
too selected to carry the result alone.

## Overall matched results

| Concordance | GHS-POP boundary | Source | N | Persistence beta | MAE improvement vs zero | RMSE improvement vs zero | Sign reversal |
|---|---|---|---:|---:|---:|---:|---:|
| Dynamic identity | Fixed origin DID | Direct count | 874 | 0.622 | 0.178 pp | 0.152 pp | 24.9% |
| Dynamic identity | Fixed origin DID | GHS-POP | 874 | 0.513 | 0.274 pp | 0.129 pp | 14.6% |
| Dynamic identity | Dynamic DID | GHS-POP | 874 | 0.449 | 0.061 pp | -0.055 pp | 27.3% |
| Strict stability | Fixed origin DID | Direct count | 74 | 0.812 | 0.576 pp | 0.814 pp | 14.9% |
| Strict stability | Fixed origin DID | GHS-POP | 74 | 0.721 | 0.147 pp | 0.136 pp | 35.1% |
| Strict stability | Dynamic DID | GHS-POP | 74 | 0.711 | 0.143 pp | 0.130 pp | 35.1% |

The direct-count coefficient exceeds GHS-POP in every overall comparison. GHS-POP has a better MAE
gain and lower reversal rate only in the high-coverage fixed-origin comparison; its RMSE gain is
smaller. On the strict sample, direct counts dominate both GHS-POP treatments on coefficient,
MAE/RMSE gain, and reversal rate. That is not a materially stronger GHSL persistence pattern.

## Period consistency

Direct-count persistence improves both MAE and RMSE over zero growth at each origin—2005, 2010, and
2015—under both concordance rules. The dynamic-identity direct coefficients decline from 0.724 to
0.646 to 0.533, so persistence weakens over time rather than remaining structurally constant.

GHS-POP is less stable. Under fixed origin polygons, its dynamic-identity coefficient is 0.183 in
2005, 0.740 in 2010, and 1.053 in 2015; the 2005 RMSE gain is negative. Under dynamic polygons, its
RMSE gain is negative in 2005 and 2010. The fixed-footprint signal is therefore highly
period-sensitive, not uniformly smoothed upward relative to direct counts.

## Evidentiary limit

This closes the narrow issue #124 falsification: a matched direct-count benchmark now exists and it
does not show systematically stronger GHSL persistence. It weakens construction smoothing as the
explanation for the earlier GHSL/WUP divergence.

It does not establish universal H1. The strict sample covers only 7.2% of the origin denominator,
Japan is one national system, GHS-POP remains a modeled allocation, and the comparison uses a zero-
growth reference rather than the full registered hierarchy of country, size, and spatial models.
The defensible claim is independent support for recent-growth persistence among matched Japanese
DIDs, with strong geographic-selection and external-validity limits.

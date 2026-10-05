# GHSL construction smoothing against direct locality counts

Issue #124 is implemented as a matched, fail-closed red-team benchmark. It does not
promote GHSL to independent confirmation of H1.

The comparison fixes each national origin denominator before concordance or endpoint
eligibility is evaluated. Unresolved localities remain in the coverage output. Only
locality-period rows eligible in both the direct-count and GHSL streams enter the paired
diagnostics, so future entrants cannot define membership.

For the identical matched rows, the benchmark reports recent/future OLS coefficients,
persistence and zero-growth MAE/RMSE, improvement over zero growth, sign reversals, and
signed and absolute growth curvature. Results are stratified by official concordance
quality, census recency, and GHSL boundary mode. The contrast table is always expressed
as GHSL minus direct counts.

## U.S. pilot decision

The registered U.S. Census place pilot contains direct enumerations for 2010 and 2020.
Those two waves yield one growth interval, not a recent-growth predictor followed by a
future-growth outcome. The repository's persistence gate requires at least two matched
forecast origins. The current U.S. benchmark is therefore **not estimable** and remains
unresolved pending a third direct-count wave plus defensible official adjacent-wave
concordances.

`scripts/run_construction_smoothing_124.py` writes this decision to
`outputs/construction_smoothing_124/benchmark_status.csv`. If registered direct-count
and GHSL interval files are supplied later, the same runner produces denominator
coverage, matched source metrics, and GHSL-minus-direct contrasts. Similarity would
weaken the smoothing explanation but would not prove construction effects absent;
materially stronger GHSL persistence would be evidence consistent with smoothing.

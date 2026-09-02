# Density metric registry

`src/urban_growth/density_metrics.py` is the executable policy for Module C density
measures. `data/density_metric_registry.csv` is its registered, reviewable output. A test
requires the two representations to match exactly.
`data/density_metric_pair_registry.csv` separately registers every predictor/outcome pairing;
this prevents a metric-level `clean` label from being treated as universal permission.
The registered outcome universe includes direct-census and GHS-POP density outcomes plus WUP,
GHS-POP and direct-census population growth. Built-form predictors paired with either publisher
population-growth outcome are sensitivity-only; the corresponding direct-census pair is
headline-admissible on validated enumerated support.

Each metric row fixes the ID, numerator and denominator sources, log-ratio formula, lineage
scope, reported epochs, first admissible forecast origin, level/change estimands, roles and
temporal constraint. Downstream
density outputs use `attach_density_metric_references`; an unknown metric ID fails closed.

## Headline restrictions

Metrics derived from WUP F21 or GHS-POP are `lineage_entangled`. They are sensitivity-only,
including population per land area: changing its denominator does not erase the numerator's
built-layer lineage. The role guard rejects these metrics as either C1 outcomes or C3
origin-available predictors.

Direct-census density metrics are clean only when the count remains direct enumeration on its
registered support or uses a separately documented polygon allocation. The registry does not
waive the census geography gate.

Built surface per land area is clean of population allocation only against a direct-count
outcome. Against WUP or GHS-POP it is registered sensitivity-only. Volume per surface is also
free of a population numerator, but it is a level-only spatial descriptor and is neither an
outcome nor a vertical-growth series. Its level may predict a later change outcome when timing
permits; that does not turn the predictor itself into a change measure. All `GH_BUV_*` epochs use the fixed 2018
height layer. Their reported epochs begin in 1975, while their first valid forecast origin is
2020. This distinction prevents a constructed historical epoch from being treated as information
available before its height input existed.

All measures use log ratios. Any annualized change is therefore the difference in logged ratios
divided by the exact interval length, consistent with the project's population-growth convention.

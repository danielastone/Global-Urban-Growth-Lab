# WUP red-team findings 5–8

## Finding 5 — missing contemporaneous country comparator

Confirmed. The historical baseline ladder uses past realized outcomes. It did not include the origin-available cross-sectional mean of `recent_growth` among the focal city's other same-country cities at the same forecast origin.

The new diagnostic in `urban_growth.contemporaneous_baseline` adds exactly that comparator. It is leave-city-out. A singleton-country city falls back to the global contemporaneous leave-city-out mean. Future outcome growth is never used in constructing the predictor.

Interpretation: this comparator directly tests whether a city's own persistence signal beats the contemporaneous growth state of peer cities in the same country. It is especially relevant to distinguishing city-specific persistence from convergence toward a current national urban-growth regime.

## Finding 6 — hierarchy model does not provide the required per-origin H1 test

Partly superseded. The original `evaluate_rolling_hierarchy_models` remains a hierarchy-model diagnostic and should not be reinterpreted as the decisive H1 test. However, PR #122 added a separate per-origin nested diagnostic comparing leave-city-out country context with the same baseline plus recent city growth, trained only on prior outcomes. PR #123 executed that diagnostic on observed/reference-estimate WUP outcomes through 2015->2020.

That newer test should be cited for the incremental-information question. The older pooled hierarchy model remains useful for specification comparison, not as the sole H1 falsification instrument.

## Finding 7 — comparator drift across bootstrap outputs

Confirmed. Historical outputs were not comparator-identical:

- the default one-way size-bin paired/bootstrap path used `country_mean`;
- the size-bin two-way bootstrap explicitly used `country_mean`;
- the pooled two-way bootstrap defaulted to `country_mean_leave_city_out`.

The numerical distinction is small, but the provenance distinction is real. Existing registered files keep their original semantics and hashes; they must not be described generically as one comparator. New persistence-vs-country inference should name the exact `model_b` field, with leave-city-out preferred when the estimand is a distinct country component.

No historical manifest is silently rewritten by this correction.

## Finding 8 — aggregation-ladder bootstrap does not refit means

Confirmed. The current aggregation-ladder bootstraps operate on precomputed row-level errors. Resampling country clusters therefore changes the weighting of errors but does not recompute global, region, or subregion means inside each bootstrap draw.

Those intervals are conditional-on-fitted-baselines intervals, not full refit bootstrap intervals. This matters most for region-vs-global and subregion-vs-region comparisons; leave-city-out country means are much less affected because their fitted component is local to the resampled cluster.

Until a refit bootstrap is implemented, aggregation-ladder confidence intervals must be labeled `conditional_on_fitted_baselines`. Point estimates remain valid. A future refit implementation must resample whole country clusters, clone repeated clusters with unique bootstrap identifiers, recompute the aggregation means within every draw using only training rows available at each origin, then rescore the same nested aggregation comparison.

## Priority

1. Execute the contemporaneous-country comparator on the corrected WUP observed lineage.
2. Treat PR #122/#123 as the per-origin H1 incremental-information result, not the older hierarchy table.
3. Keep historical bootstrap comparator names explicit.
4. Replace aggregation-ladder conditional intervals with refit intervals before using them for strong inferential claims.

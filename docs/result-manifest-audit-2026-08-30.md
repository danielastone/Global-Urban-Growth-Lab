# Result-manifest audit — 2026-08-30

## Decision

Do not refresh the expected-result hashes as a mechanical maintenance action. The
existing manifests combine three different states: historically reproducible outputs,
intentional post-manifest specification changes, and six byte-level results that do
not reproduce even under the historical code. Replacing all hashes together would
erase those distinctions.

## Inputs recovered

All eight files registered in `data/manifest.csv` were reacquired from their official
endpoints. Every archive and workbook matched its recorded SHA-256 hash. The extracted
WUP 2018 F22 workbook also matched its separately registered hash. Raw files remained
outside Git.

## Historical replay

All four expected manifests were created in commit `cfae942` on 28 August 2026. That
commit did not contain `uv.lock`; dependency locking was added later in `d7d432d`.
The `cfae942` code was replayed in an isolated worktree against the exact registered
inputs, using the repository's current locked environment.

| Manifest family | Historical replay result | Interpretation |
|---|---|---|
| WUP 2018 vintage | Fully verified | Historical hash, dimensions, and code path remain reproducible. |
| WUP 2025 | All expected files verified except two temporal diagnostics | Core historical outputs reproduce; temporal byte hashes do not. |
| GHSL fixed | All expected files verified except two temporal diagnostics | Core historical outputs reproduce; temporal byte hashes do not. |
| GHSL boundary | Coverage and metric outputs verified; two temporal diagnostics failed hashes | Dimensions reproduce; temporal byte hashes do not. |

The six non-reproducing historical files are:

- `outputs/wup_temporal_reversal_diagnostics.csv`
- `outputs/wup_gapped_temporal_diagnostics.csv`
- `outputs/ghsl_fixed_temporal_diagnostics.csv`
- `outputs/ghsl_fixed_gapped_temporal_diagnostics.csv`
- `outputs/ghsl_boundary_fixed_matched_temporal.csv`
- `outputs/ghsl_boundary_dynamic_matched_temporal.csv`

Their dimensions match the manifests. Replaying both historical and current code in
the current locked environment produces identical hashes for these six files, but
those hashes differ from the pre-lock expected hashes. The historical CSV bytes were
not retained, so the repository cannot prove whether the difference is numeric,
formatting-only, or dependency-driven. It must not describe these six byte hashes as
reproducible.

## Current-code drift

The manifests were not refreshed after substantial forecast changes merged later on
28 August. Relevant changes include sample-selection auditing, WUP vintage
decomposition, focal-city exclusion from the national comparator, equal-origin
estimands, locked-origin evaluation, and interval-calibration corrections.

### WUP 2025

The former single model `national_city_category_persistence` became separate
inclusive and leave-city-out diagnostics. The primary rolling metric tables therefore
change from 88 to 96 rows; the gapped table changes from 66 to 72 rows. The valid
leave-city-out diagnostic also excludes 264 city-origin rows across 55 countries where
F01 minus F21 is nonpositive at one or both endpoints. All baseline models are scored
on the resulting common finite sample.

At the 2020 origin, country- and city-influence outputs each lose 25 invalid focal
systems relative to the historical manifest. Bootstrap and weighting outputs retain
their structural dimensions but change numerically because their common sample
changes.

### WUP 2018 vintage

The metrics file retains 180 rows. It grows from 12 to 15 columns through three audit
fields:

- `eligible_for_like_for_like_2018_ranking`
- `predictor_information_set`
- `target_comparability`

This is a schema change from the vintage-comparability decomposition, not observation
attrition.

### GHSL

All expected non-temporal GHSL outputs still reproduce under current code. The only
GHSL failures are the same four pre-lock temporal byte hashes identified by the
historical replay.

## Required remediation

The remediation was completed after the numerical review of the corrected common
sample:

1. The original manifests are preserved unchanged under
   `results/historical/cfae942/` as evidence of their historical scope.
2. The current WUP result changes, including the 2020 ranking and undefined national
   residual exclusions, were reviewed before new expectations were recorded.
3. Current manifests bind each artifact to the generating code commit, `uv.lock`
   hash, source-manifest hash, and generation command.
4. Each current entry stores both the exact CSV byte hash and a canonical numeric hash
   after floating-point values are rounded to 12 decimal places. Exact hashes still
   detect serialization changes; canonical hashes help identify whether those changes
   survive the declared numeric normalization.
5. The manifest builder records every CSV produced by each of the four registered
   generation commands. Outputs outside those four families remain outside this
   verification claim.

The current manifests can be rebuilt with `scripts/build_result_manifest.py` and
verified with `scripts/verify_results.py`. Updating an expectation is a reviewable
change: rerun the registered generation command, inspect the numerical diff, then
record the reviewed generating commit and provenance.

## Claim consequence

The exact inputs are recovered and executable, and current WUP claims have been
reviewed on the corrected common sample. Six historical temporal byte hashes remain
non-reproducible because the environment was locked after the expectations were
created; archiving those manifests preserves that limitation instead of rewriting it.

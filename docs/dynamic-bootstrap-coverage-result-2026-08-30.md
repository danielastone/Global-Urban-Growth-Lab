# Dynamic-bootstrap coverage result — 2026-08-30

## Status

The predeclared uncertainty-calibration gate failed. This is a retained negative result, not a workflow failure and not a reason to relax the gate.

## Reproducible run

- Workflow: `.github/workflows/dynamic-bootstrap-coverage.yml`
- Successful run: `33312725082`
- Producing commit: `ba02a4d2f5d2975cef141babf62570c51de917e4`
- Artifact ID: `9732905767`
- Artifact name: `dynamic-bootstrap-coverage-combined`
- Artifact SHA-256: `a1b9c86ba4ee470280c770de656742368e2d4dbd267b32fd016bc3a4fa4268c9`
- Original artifact expiry: `2026-11-28T12:54:09Z`

The exact recovered CSV is retained at `results/evidence/dynamic-bootstrap-coverage/dynamic_bootstrap_coverage.csv`. Its SHA-256 is `fbe939575ddf8d3341798aaef64bd3d539210bd70e90fc75f8f777899f9a07cf`, matching the previously committed expected manifest.

## Result

The output contains 27 rows: three estimators across nine persistence-by-panel-length cells. Only the half-panel-jackknife rows were eligible for the locked coverage gate. Those nine rows all covered 200 of 200 simulated panels, giving empirical coverage 1.0 and a Wilson interval of approximately [0.9812, 1.0]. Because that interval is not wholly inside the predeclared [0.90, 0.99] band, all nine eligible cells fail for overcoverage.

The pooled and uncorrected city-fixed-effect rows remain diagnostics. They are not eligible for this gate and are not additional gate failures.

## Interpretation

The interval is too conservative to be treated as calibrated uncertainty. Thresholds and simulation design remain unchanged. Any estimator or interval redesign is separate prospective work and must not overwrite this failed result.

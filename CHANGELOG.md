# Changelog

## Unreleased

- Decompose WUP 2018-to-2025 growth-score discrepancies into target and origin revision gaps.
- Label retrospective persistence as a hindsight diagnostic rather than a like-for-like 2018 benchmark.

## 0.1.0 — 2026-08-28

First reproducible research-foundation release.

### Included

- Separate WUP and GHSL rolling-origin forecasting workflows.
- Fixed-2025 and dynamic-boundary GHSL sensitivity analysis on matched rows.
- Actual WUP 2018 vintage evaluation against WUP 2025 estimates.
- Country-clustered, country-and-time, equal-country and influence diagnostics.
- Explicit match-coverage and crosswalk-selection audits.
- Registered source checksums and pinned result hashes and dimensions.
- Cross-platform locked Python environment and protected GitHub Actions checks.

### Principal limitations

- WUP and GHSL use different urban definitions and are not pooled.
- Fixed 2025 GHSL polygons remove changing-boundary arithmetic but use future
  geographic information when applied to historical populations.
- Most WUP rolling-origin results use revised history rather than information
  vintages available at each forecast origin.
- The WUP 2018 vintage comparison is restricted to a selected matched sample of
  large agglomerations and does not validate small-city forecasts.
- Raw source files and generated empirical CSVs are not redistributed; exact
  permitted inputs must be acquired and registered locally.
- No project-wide software license has been selected, so this release does not
  grant reuse rights beyond those already provided by law or source licenses.

### Reproduction

Use the commands in `README.md`. The committed `uv.lock` fixes the software
environment, while `data/manifest.csv` and the files under `results/` identify the
expected empirical inputs and outputs.

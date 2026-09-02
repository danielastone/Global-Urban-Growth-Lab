# Changelog

## Unreleased

- Pre-register the lineage-clean open-covariate density model, comparator ladder, country-cluster
  falsification rule, fixed failure language, and fail-closed real-run gate.

- License repository software under Apache-2.0 while explicitly excluding
  third-party data from that grant.
- Add a deny-by-default, machine-readable data-rights registry covering research,
  commercial, redistribution, model-fitting, and customer-output uses.
- Enforce catalog/license completeness in GitHub Actions and provide a failing
  `check-license` gate for every decision not explicitly marked `permitted`.
- Document attribution, IGO immunity, database-rights, IPUMS, and artifact-lineage
  boundaries in `THIRD_PARTY_DATA.md`.
- Adopt the 29 August 2026 locked empirical specification and encode its
  forecast-origin tier, ILR, census-threshold, accessibility-band, and C1/C2/C3
  form-timing contracts as tested utilities.
- Register the Malaria Atlas Project 2015 accessibility layer explicitly as a
  modern validation snapshot rather than a historical panel.
- Add equal-origin and equal-country-within-origin forecast estimands to prevent changing temporal coverage from silently determining pooled results.

- Add a focal-city-excluded WUP F01 national Cities-category comparator and retain the inclusive version only as a diagnostic.

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

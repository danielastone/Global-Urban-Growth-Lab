# Global Urban Growth Lab

A reproducible research program testing what can—and cannot—forecast population growth across the global urban hierarchy.

For version history and citation metadata, see [CHANGELOG.md](CHANGELOG.md) and
[CITATION.cff](CITATION.cff).

Repository software is licensed under Apache-2.0. Third-party datasets are not.
See [THIRD_PARTY_DATA.md](THIRD_PARTY_DATA.md) before acquiring, processing, or
redistributing data.

Contributions should begin with [CONTRIBUTING.md](CONTRIBUTING.md) and the
[implementation roadmap](https://github.com/danielastone/Global-Urban-Growth-Lab/issues/33).
The project accepts code, documentation, reproducibility, and falsification work, but
manual data, licensing, geography, and governance blocks require evidence before code.

## Research question

How much incremental out-of-sample forecasting value comes from a city's recent growth, initial size, hierarchy position, national demography, urbanization stage, spatial context, and common shocks?

The project separates three claims that are often blurred:

1. **Description:** how growth differs across observed city sizes and ranks.
2. **Forecasting:** whether information available at time `t` improves predictions after `t`.
3. **Causation:** whether changing a factor would change subsequent growth.

This repository currently supports the first two as research targets. It does not claim causal identification.

## Current status

**Baseline sensitivity stage.** WUP and GHSL rolling-origin results are regenerated from registered inputs by committed code. They disagree materially at 2020 when GHSL geography is held to fixed 2025 polygons. The immediate objective is to explain that source/definition sensitivity—not to commercialize an unstable headline.

## Primary hypotheses

| ID | Hypothesis | Main test | Falsification condition |
|---|---|---|---|
| H1 | Recent city growth contains the strongest city-level predictive signal. | Rolling-origin comparison with national and size-only baselines. | It fails to improve held-out MAE/RMSE consistently across periods and regions. |
| H2 | Initial size is mainly descriptive after persistence, country-period conditions, and selection are controlled. | Nested models, threshold sensitivity, balanced panels, and survivor reweighting. | Size remains stable, large, and incrementally predictive across designs. |
| H3 | Smaller cities are harder to forecast, even if their ordinary growth variance is not much larger. | Size-stratified forecast errors with paired bootstrap intervals. | Error distributions are equivalent after coverage and measurement-quality controls. |
| H4 | National demography and urbanization stage explain more shared variation than broad global shocks. | Country-period, region-period, and global-period decompositions. | Higher aggregation performs as well out of sample and country components add little. |
| H5 | Borders condition spatial spillovers beyond distance and accessibility. | Matched within/between-border comparisons and border-placebo tests. | Border terms vanish under comparable distance and accessibility specifications. |

See [docs/locked-specification.md](docs/locked-specification.md) for the governing empirical
contract and [docs/research-design.md](docs/research-design.md) for the accumulated estimands,
validation results, and test order.

The [result-manifest audit](docs/result-manifest-audit-2026-08-30.md) separates
historically reproducible outputs, intentional post-manifest specification changes,
and pre-lock byte-level drift. Expected hashes must not be refreshed without following
that audit's remediation steps.

## Repository structure

```text
data/                   metadata only; raw restricted data stay outside Git
docs/                   research design, status, and data contract
src/urban_growth/       reusable panel and forecast utilities
tests/                  unit tests for leakage-prone transformations
outputs/                generated tables and figures (not hand-edited)
```

## Quick start

```bash
uv sync --locked --extra dev
uv run --locked --extra dev pytest
```

The committed `uv.lock` resolves exact, cross-platform dependency versions. Use the
locked commands above for research reproduction; installing directly from the broad
minimum versions in `pyproject.toml` can produce a different environment.

The package does not download source data automatically. Register every input in `data/manifest.csv`, place permitted local files under `data/raw/`, and build analytical panels through code. The WUP workflow requires F01 plus the F21/F25/F30/F34 city workbooks; F01 provides the national Cities-category comparator.

Inspect the authoritative source catalog and inventory local downloads with:

```bash
urban-growth-sources list
urban-growth-sources verify-catalog
urban-growth-sources verify-licenses
urban-growth-sources inventory data/raw/<file> --source-id <source_id>
```

The catalog is documented in [docs/source-library.md](docs/source-library.md). WUP 2025 supplies demographic city records and national controls, but those results are not geography-controlled. GHSL supplies the fixed-polygon sensitivity layer, not an independent replication. The two sources remain separate analytical panels.

Run the registered baseline workflows separately:

```bash
python scripts/run_wup_baselines.py
python scripts/run_wup2018_vintage.py
python scripts/run_ghsl_fixed_baselines.py
python scripts/run_ghsl_boundary_sensitivity.py
python scripts/verify_results.py \
  results/wup_expected_manifest.csv \
  results/wup2018_vintage_expected_manifest.csv \
  results/ghsl_fixed_expected_manifest.csv \
  results/ghsl_boundary_expected_manifest.csv
```

The GHSL workflow accepts only the fixed-2025 boundary product and first reconciles it to the quality-controlled 2025 multi-temporal stream. Fixed polygons eliminate changing-boundary arithmetic but introduce a 2025-boundary look-ahead. The result is a retrospective fixed-footprint sensitivity, not historically validated geography or real-time forecasting.

The boundary-sensitivity workflow then restricts fixed and dynamic GHSL streams to identical identifiers, countries, origins and complete forecast rows. Their outcomes remain definition-specific and are never treated as interchangeable ground truth.

Generated CSVs remain outside Git, but the expected file hashes and dimensions are committed under `results/`. Verification therefore detects undocumented changes in default outputs. GitHub Actions validates code and unit tests only because raw source files are not committed; it does not reproduce the empirical tables.

## Minimum analytical panel

One row represents a stable urban unit in one period. Required fields are documented in [docs/data-contract.md](docs/data-contract.md). Growth is calculated as an annualized log difference, and every predictor must be observable no later than the forecast origin.

## Evidence gate

A numerical claim may move from “reconstruction target” to “result” only when the repository contains:

- a versioned source and retrieval record;
- stable city identifiers and boundary treatment;
- scripted transformation into the analytical panel;
- an explicit training and test design;
- uncertainty that respects country and time dependence;
- generated output; and
- at least one serious falsification or sensitivity test.

## Data and licensing

Do not commit restricted, employer-owned, or redistribution-uncertain data. Dataset
terms remain controlling. Apache-2.0 covers software only; no project-data license has
been selected and data reuse rights are not implied. `data/licenses.json` denies an
operation unless its source-specific decision is explicitly `permitted`.

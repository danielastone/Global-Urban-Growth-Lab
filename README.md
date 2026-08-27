# Global Urban Growth Lab

A reproducible research program testing what can—and cannot—forecast population growth across the global urban hierarchy.

## Research question

How much incremental out-of-sample forecasting value comes from a city's recent growth, initial size, hierarchy position, national demography, urbanization stage, spatial context, and common shocks?

The project separates three claims that are often blurred:

1. **Description:** how growth differs across observed city sizes and ranks.
2. **Forecasting:** whether information available at time `t` improves predictions after `t`.
3. **Causation:** whether changing a factor would change subsequent growth.

This repository currently supports the first two as research targets. It does not claim causal identification.

## Current status

**Reconstruction stage.** Earlier exploratory estimates are recorded in [docs/research-status.md](docs/research-status.md), but they are not findings until regenerated from frozen inputs by committed code. The immediate objective is a defensible forecasting benchmark, especially for smaller cities—not a prematurely commercialized forecast product.

## Primary hypotheses

| ID | Hypothesis | Main test | Falsification condition |
|---|---|---|---|
| H1 | Recent city growth contains the strongest city-level predictive signal. | Rolling-origin comparison with national and size-only baselines. | It fails to improve held-out MAE/RMSE consistently across periods and regions. |
| H2 | Initial size is mainly descriptive after persistence, country-period conditions, and selection are controlled. | Nested models, threshold sensitivity, balanced panels, and survivor reweighting. | Size remains stable, large, and incrementally predictive across designs. |
| H3 | Smaller cities are harder to forecast, even if their ordinary growth variance is not much larger. | Size-stratified forecast errors with paired bootstrap intervals. | Error distributions are equivalent after coverage and measurement-quality controls. |
| H4 | National demography and urbanization stage explain more shared variation than broad global shocks. | Country-period, region-period, and global-period decompositions. | Higher aggregation performs as well out of sample and country components add little. |
| H5 | Borders condition spatial spillovers beyond distance and accessibility. | Matched within/between-border comparisons and border-placebo tests. | Border terms vanish under comparable distance and accessibility specifications. |

See [docs/research-design.md](docs/research-design.md) for estimands, validation rules, and test order.

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
python -m venv .venv
python -m pip install -e ".[dev]"
pytest
```

The package does not download source data automatically. Register every input in `data/manifest.csv`, place permitted local files under `data/raw/`, and build analytical panels through code.

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

Do not commit restricted, employer-owned, or redistribution-uncertain data. Dataset terms remain controlling. No project-wide license has yet been selected, so reuse rights are not implied.

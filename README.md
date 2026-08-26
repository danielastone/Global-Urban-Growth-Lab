# Global Urban Growth Lab

A reproducible research project examining what predicts city growth and decline across the global urban hierarchy.

## Central question

How much of a city's subsequent population growth can be explained by recent city growth, national demography, urbanization, initial city size, hierarchy position, spatial context, and common shocks?

## Current status

**Research reconstruction in progress.**

Substantial exploratory and robustness analysis was completed before this repository was created. The code, frozen inputs, and generated outputs have not yet been committed. Results below are therefore **preliminary research records, not independently reproducible findings**.

## Preliminary findings to reproduce

- Recent city growth appears to be the strongest forecasting signal.
- Initial city size is more useful descriptively than causally; part of the observed size effect reflects persistence, sorting, and survivorship.
- Estimated within-urban growth persistence was approximately **0.72 per five-year period**, corresponding to a rough half-life near **10.7 years**.
- The cross-sectional size gradient was approximately **+0.19 percentage points of annual growth per population doubling**.
- After geometry and sample cleaning, ordinary growth volatility appeared nearly size-independent, with an estimated size exponent near **0.03**.
- Entry into a negative-growth state was more common among smaller cities: approximately **24.5%**, compared with **12.3%** among cities above two million residents.
- A national urban-hierarchy-depth interaction was estimated near **0.025–0.028** across several specifications.
- Moderation by the speed of national urbanization was suggestive, not established.

These values are reconstruction targets. They should not be cited as final estimates until this repository reproduces them from documented source data.

## Working interpretation

```text
city growth
= national demography
+ change in national urban share
+ redistribution within the urban system
+ city-specific shocks
```

> Recent growth carries the most predictive information. City size mainly captures descriptive hierarchy, persistent trajectory, and selection effects rather than a simple causal protection against decline.

## Evidence base

Prior work used global urban-population sources including World Urbanization Prospects and DEGURBA-related evidence. A full cities/towns/rural stage-variable analysis remains incomplete because required source spreadsheets were unavailable in the earlier workflow.

No restricted or employer-owned data should be committed.

## Reproduction standard

A result is reproduced only when the repository contains:

- a stable source citation and retrieval record;
- a documented transformation into the analytical panel;
- code generating the estimate;
- generated tables or figures;
- sample and exclusion rules;
- uncertainty estimates; and
- a relevant robustness or falsification test.

## Planned structure

```text
data/
src/
notebooks/
tests/
outputs/
docs/
```

Directories will be added only when they contain working artifacts.

## Immediate sequence

1. Recover and inventory existing notebooks, scripts, source files, tables, and figures.
2. Freeze a city-period panel with stable identifiers.
3. Reproduce persistence and size-gradient estimates.
4. Reproduce threshold, geometry, bootstrap, and jackknife checks.
5. Build rolling out-of-sample benchmarks.
6. Add national, regional, global, and spatial decompositions.

## Research discipline

Descriptive association, forecasting performance, and causal identification are separate claims. A predictive coefficient is not evidence that changing city size would change growth.

## License

No license has been selected. Source datasets retain their original terms and must be reviewed before redistribution.

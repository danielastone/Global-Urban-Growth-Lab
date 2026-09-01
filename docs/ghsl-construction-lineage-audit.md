# GHSL construction-lineage red-team audit

## Finding

The fixed-boundary GHSL persistence result is **not an independent replication of city-growth persistence**. It is a construction-sensitive robustness result produced from a modeled spatial population surface inside a future-defined 2025 footprint.

This distinction is separate from the already documented boundary look-ahead and future-survivor problems.

## Why the population series is not direct city enumeration

The GHS-POP family distributes census or administrative-unit population to grid cells using GHSL built-up information. For the historical 1975–2020 epochs, population totals ultimately originate in census/administrative data, but the population assigned to a particular urban-centre footprint is a modeled spatial allocation rather than a direct enumeration of that footprint.

Official JRC references:

- GHS-POP R2023A dataset page: https://data.jrc.ec.europa.eu/dataset/2ff68a52-5b5b-4a22-8f40-c41da8332cfe
- GHS-BUILT-S R2023A dataset page: https://data.jrc.ec.europa.eu/dataset/9f06f36f-4b11-47ec-abb0-4f8b7b1d72ea
- GHSL WUP population methodology: https://human-settlement.emergency.copernicus.eu/ghs_wup_pop_r2025a.php

The built-up series used to inform spatial allocation is itself multitemporal modeled data. JRC describes GHS-BUILT-S as spatial-temporal interpolation of a limited set of observed satellite-image collections. That creates a plausible mechanical channel through which local population histories can be smoother than direct locality counts even when higher-level population totals are census anchored.

## Evidence already inside this repository

The repository's matched fixed-versus-dynamic GHSL sensitivity provides direct evidence that construction choices materially affect apparent persistence:

- fixed-2025-footprint persistence MAE: 0.758 percentage points;
- dynamic-footprint persistence MAE: 1.274 percentage points;
- fixed-2025-footprint persistence RMSE: 1.334 percentage points;
- dynamic-footprint persistence RMSE: 2.268 percentage points;
- 2020 within-country recent/future correlation: 0.764 fixed versus 0.532 dynamic.

Holding the footprint fixed therefore makes the same source family substantially smoother and persistence substantially stronger. This does not prove that population disaggregation is the cause, but it demonstrates that the strength of the persistence signal is sensitive to the source-construction package.

## What can and cannot be concluded

Allowed interpretation:

> Within the retrospective GHSL modeled population surface, recent growth remains highly predictive when population is measured repeatedly inside the same 2025 urban-centre footprint.

Not allowed:

- GHSL independently confirms the real-world magnitude of city-growth persistence;
- GHSL validates the WUP persistence coefficient;
- the fixed-boundary result identifies how much persistence is demographic rather than induced by spatial allocation or footprint construction;
- stronger fixed-footprint persistence proves changing boundaries caused the WUP/GHSL disagreement.

The construction-artifact hypothesis and the true-demographic-persistence hypothesis are observationally entangled in this source.

## Required falsification test

The preferred falsification is an external direct-count benchmark, not another transformation of GHSL. For national census systems with direct locality/place counts and defensible concordances:

1. define the origin cohort before concordance exclusions;
2. estimate recent-to-future growth persistence from direct counts;
3. where possible, aggregate GHSL population to comparable locality footprints and periods;
4. compare coefficients, forecast-error deltas, sign-reversal rates, and growth curvature on the matched locality-period sample;
5. stratify by census recency and concordance quality;
6. treat a materially stronger GHSL persistence signal than the direct-count signal as evidence consistent with construction smoothing.

Until that test exists, GHSL is a sensitivity layer rather than independent confirmation of H1.

## Claim status

This audit does not invalidate the registered GHSL numerical outputs. It changes their evidentiary role. The existing outputs remain reproducible retrospective diagnostics, but they cannot upgrade a persistence claim beyond what direct-count or vintage-correct evidence supports.

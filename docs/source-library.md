# Data source library

The machine-readable catalog is `data/sources.json`. It records analytical role, coverage, provenance, dependence, retrieval method, and redistribution posture. `data/manifest.csv` records the exact local files actually used, including checksums.

## Hierarchy

| Source | Role | Use | Main limitation |
|---|---|---|---|
| WUP 2025 Cities | City statistical core | Individual-city population, area and density | Retrospective revision; 2025-threshold selection |
| WUP 2025 country DEGURBA | National control | Cities/towns/rural totals and urbanization stage | Not an individual-city panel |
| GHS-UCDB R2024A v1.2 | Spatial core | Dynamic footprint, fixed-boundary sensitivity, density, area change | Not independent of WUP/DEGURBA |
| WPP 2024 | National control | National demographic benchmark | Current-vintage history is not a real-time forecast vintage |
| OECD FUA | Mechanism | Urban core versus commuting zone | Restricted country/sample comparability |
| WorldPop Global 2 | Robustness | Fine-grid population allocation | 2015-2030 is too short for the primary historical design |
| Natural Earth Admin 0 | Spatial control | Borders and island geometry | Geometry does not measure migration-policy restrictiveness |

## Verified WUP F21 schema

The exact F21 workbook was retrieved on 2026-08-27 and registered in `data/manifest.csv`. Its `Data` sheet contains 16,828 unique `City_Code` rows and annual columns from 1975 through 2050. The annual series is threshold-truncated: a cell is blank while the city is below 50,000 and populated once it meets the reporting threshold. In the acquired workbook, 12,138 cities have 2025 values and 3,633 records are absent in 2025 but present by 2050.

Consequences:

- WUP F21 cannot by itself estimate population trajectories below 50,000.
- Applying a fresh `population >= 50,000` filter does not solve truncation.
- Entry-year, balanced-panel and near-threshold analyses must be explicit.
- GHSL fixed-entity histories are a sensitivity path, not independent evidence.

## Rules

1. Never infer a source from a filename alone; pair every file with a catalog `source_id`.
2. Save source downloads unchanged under `data/raw/` and register their SHA-256 checksum.
3. Record retrieval date and source URL. The catalog's landing page is not a substitute for the exact download URL.
4. Treat estimates, projections, interpolations, and observations as different observation types.
5. Keep GHSL dynamic-footprint and fixed-boundary streams separate.
6. Do not call GHSL an independent replication of WUP 2025.
7. Never commit a source file until redistribution terms have been reviewed for that exact product.
8. Fail on ambiguous identifiers, duplicate city-period keys, or missing year semantics.

## Acquisition order

1. WUP 2025 individual-city population and surface-area tables plus separate country/category controls.
2. GHS-UCDB R2024A v1.2 tabular attributes; acquire geometry only after the tabular pipeline is stable.
3. WPP 2024 national controls.
4. OECD FUA and WorldPop only after the core out-of-sample benchmark exists.

The repository deliberately does not automate large or license-sensitive downloads. Acquisition automation is useful only after the publisher exposes a stable, documented endpoint.

# Data source library

The machine-readable catalog is `data/sources.json`. It records analytical role, coverage, provenance, dependence, retrieval method, and redistribution posture. `data/manifest.csv` records the exact local files actually used, including checksums.

## Hierarchy

| Source | Role | Use | Main limitation |
|---|---|---|---|
| WUP 2025 Cities | City statistical core | Individual-city population, area and density | Values suppressed below 50,000 at each year |
| WUP 2025 country DEGURBA | National control | Cities/towns/rural totals and urbanization stage | Not an individual-city panel |
| GHS-UCDB R2024A v1.2 | Spatial core | Dynamic footprint, fixed-boundary sensitivity, density, area change | Not independent of WUP/DEGURBA |
| WPP 2024 | National control | National demographic benchmark | Current-vintage history is not a real-time forecast vintage |
| OECD FUA | Mechanism | Urban core versus commuting zone | Restricted country/sample comparability |
| WorldPop Global 2 | Robustness | Fine-grid population allocation | 2015-2030 is too short for the primary historical design |
| Natural Earth Admin 0 | Spatial control | Borders and island geometry | Geometry does not measure migration-policy restrictiveness |

## Verified WUP F21 schema

The exact F21 and F25 workbooks were retrieved on 2026-08-27 and registered in `data/manifest.csv`. Each `Data` sheet contains 16,828 unique `City_Code` rows and annual columns from 1975 through 2050. The annual series is threshold-truncated: a cell is blank while the city is below 50,000 and populated once it meets the reporting threshold. In F21, 12,138 cities have 2025 values and 3,633 records are absent in 2025 but present by 2050. F25 has the same non-null counts for the checked years, supporting a direct city-year join.

Consequences:

- WUP F21 cannot by itself estimate population trajectories below 50,000.
- Applying a fresh `population >= 50,000` filter does not solve truncation.
- Entry-year, balanced-panel and near-threshold analyses must be explicit.
- GHSL fixed-entity histories are a sensitivity path, not independent evidence.

## Verified GHSL R2024A v1.2 schema

The official v1.2 GHSL thematic archive was retrieved and registered on 2026-08-27. Its CSV uses Windows-1252 encoding and contains 11,422 unique `ID_UC_G0` records and 551 columns. The adapter reads 12 five-year epochs from 1975 through 2030 for both `GH_POP_TOT_YYYY` (inhabitants) and `GH_BUS_TOT_YYYY` (square metres). All 274,128 values across those two families are present, numeric and positive.

The thematic archive is the fixed-boundary stream: every historical statistic is calculated inside the urban centre's 2025 boundary. The separately published MTUC archive follows changing boundaries. GHSL documentation says the two streams are different and not comparable except at 2025. Therefore a trend from the thematic archive describes change within today's footprint; it is not the city's historical spatial expansion.

The publisher landing page still labels the release v1.1, but the official download script and archive readme identify v1.2, state that the data were last updated on 2026-05-15, and explicitly deprecate v1.1. The catalog records that discrepancy instead of silently downgrading the acquired package.

## Verified GHSL multi-temporal schema

The separate MTUC v1.2 archive contains 11,686 unique trajectories and 170 columns. Its CSV also uses Windows-1252 encoding. Population, built-up surface and urban-centre area are reported for 12 five-year epochs, but only while a centre satisfies the urban-centre definition. The declared birth and death years exactly explain every absent value: coverage grows from 5,080 centres in 1975 to 11,686 in 2025, then falls to 11,521 in 2030 because 165 centres have a declared 2025 death year.

The 264 MTUC records beyond the 11,422 quality-controlled thematic centres have no `GC_CNT_GAD_2025` country assignment. The adapter retains them with `quality_controlled_2025 = false`; it does not silently discard them or mix them into country-level analysis. Any primary country comparison must filter to the quality-controlled subset and report that exclusion. One uncontrolled trajectory lacks built-up surface for seven active epochs; those rows are retained with `built_up_area_available = false` instead of deleting otherwise valid population and area observations.

Dynamic-boundary population is itself threshold-selected: every active value is at least 50,000. The MTUC stream fixes the spatial-boundary problem but does not recover below-threshold population histories. It is therefore a boundary sensitivity analysis, not a cure for WUP truncation.

## Fixed/dynamic reconciliation at 2025

The two streams were joined at their documented common epoch. All 11,422 quality-controlled identifiers and country assignments match one-to-one. Built-up surface and urban-centre area match exactly. Population differs by no more than 0.5 person because the MTUC CSV displays whole persons while the thematic CSV retains decimals. Fourteen apparent name differences are not substantive: the thematic file uses `-` where MTUC uses a blank value. The reconciliation utility enforces these rules and fails on missing IDs, country disagreement, nonzero area disagreement, or population differences beyond the publisher's rounding precision.

This reconciliation validates the join and the 2025 common point. It does not make fixed- and dynamic-boundary histories interchangeable before 2025.

## WUP–GHSL identifier audit

WUP `City_Code` is not GHSL `ID_UC_G0`. Although 11,420 numeric values appear in both columns, direct inspection proves the overlap is coincidental: for example, WUP code 1881 is Andkhoy, Afghanistan, while GHSL ID 1881 is Bandırma, Turkey. A direct numeric join would look almost complete while assigning most cities to the wrong country.

The spatial audit also rejects a naive one-to-one point-in-polygon crosswalk. Of 12,138 WUP cities reported in 2025, 11,161 points fall inside a quality-controlled GHSL 2025 polygon, covering 10,918 GHSL centres. Some polygons contain multiple distinct WUP cities. Even exact normalized names leave five GHSL centres with multiple same-named WUP candidates, including Nanchang, Mandalay, Yangon, Hpakant and Biratnagar. These are definition and aggregation conflicts, not clerical duplicates that can be discarded automatically.

Consequences:

- Use WUP population with WUP area through `City_Code` for the primary WUP panel.
- Use GHSL population, built-up surface and geometry through `ID_UC_G0` for the GHSL boundary analysis.
- Do not merge the two panels row-by-row until a reviewed spatial/name/country crosswalk exists.
- Treat many-WUP-to-one-GHSL cases as an explicit aggregation decision with double-counting checks.
- Use the two internally coherent panels as sensitivity analyses rather than forcing a false unified city identity.

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

# Data source library

The machine-readable catalog is `data/sources.json`. It records analytical role, coverage, provenance, dependence, retrieval method, and redistribution posture. `data/manifest.csv` records the exact local files actually used, including checksums.

## Hierarchy

| Source | Role | Use | Main limitation |
|---|---|---|---|
| WUP 2025 Cities | City statistical core | Individual-city population, area and density | Values suppressed below 50,000 at each year |
| WUP 2025 country DEGURBA | National control | Cities/towns/rural totals and urbanization stage | Not an individual-city panel |
| GHS-UCDB R2024A v1.2 | Spatial core | Dynamic footprint, fixed-boundary sensitivity, density, area change | Not independent of WUP/DEGURBA |
| WPP 2024 | National control | National demographic benchmark | Current-vintage history is not a real-time forecast vintage |
| MAP accessibility 2015 | Modern validation | Mutually exclusive travel-time rival-mass bands | A 2015 snapshot, not a historical panel |
| OECD FUA | Mechanism | Urban core versus commuting zone | Restricted country/sample comparability |
| WorldPop Global 2 | Robustness | Fine-grid population allocation | 2015-2030 is too short for the primary historical design |
| Natural Earth Admin 0 | Spatial control | Borders and island geometry | Geometry does not measure migration-policy restrictiveness |
| U.S. Decennial Census places | Threshold validation | Direct 2010/2020 place counts and official relationship file | Favorable single-country pipeline test; not Global South feasibility evidence |
| Mexico INEGI locality census and geography | Threshold validation | Direct 2010/2020 locality counts, official equivalence records and vintage geometry | Exact files and national concordance coverage have not yet been audited |

## U.S. Decennial Census place pilot

The initial threshold-pipeline validation uses the 2010 Decennial Census SF1 total
population field `P001001`, the 2020 Decennial Census PL 94-171 total population field
`P1_001N`, and the official national 2020-place to 2010-place relationship file. The
population calls cover the 50 states and District of Columbia. The raw API responses
are retained rather than replacing them with derived estimates.

The relationship file supplies both place GEOIDs, both endpoint land areas, and the
intersection land area. Analysis is restricted to one-to-one mappings with at least
99.5% land overlap against each endpoint. This is an auditable screen for boundary
comparability, not a claim that land overlap alone harmonizes population definitions.
Exact files enter `data/manifest.csv` only after credentialed acquisition and hashing.
The U.S. source validates pipeline behavior but cannot satisfy the separate Global
South census-feasibility requirement.

## Mexico INEGI locality-concordance pilot

The first Mexico interval is 2010–2020. Direct locality population comes from INEGI
SCITEL/ITER. Geographic-key relationships come from the Catálogo Único and are reviewed
against the Archivo Histórico de Localidades. Comparable-geography screening uses the 2010
and 2020 Marco Geoestadístico locality layers.

The nine-digit locality key contains state, municipality and locality components. A municipal
change can therefore rekey an otherwise related locality, while a repeated key does not rule
out a boundary event. Key equality is only candidate evidence. Name and coordinate matching
may locate candidates but cannot create an accepted concordance.

These sources are not added to `data/sources.json` or `data/manifest.csv` until the exact
downloads, product versions, redistribution terms and hashes are known. Source availability
establishes feasibility in principle only; G2 remains open until count- and population-weighted
coverage and every split/merge exclusion are reported. The full acquisition and acceptance
contract is in `docs/mexico-locality-concordance-feasibility.md`.

## Verified WUP F01 national control

The official F01 workbook was retrieved on 2026-08-27 and registered with its exact
URL and SHA-256 checksum. Its `Cities` sheet contains 237 unique Country/Area rows
and annual harmonized Cities-category populations for 1950–2050. The adapter rejects
aggregate rows, requires ISO3 country codes, converts thousands to persons, and
preserves estimate-versus-projection status.

For each city forecast origin, the national comparator annualizes log growth in the
country's F01 Cities-category population from `origin - 5` through `origin`. It never
uses the national value after the origin. This is a genuine national demographic
comparator, unlike the repository's `country_mean`, which averages historical city
outcomes in the analytical sample. It is still revised-history evidence from WUP
2025, not the national forecast vintage available at the historical origin.

F01 also supplies 22 geographic subregions and six terminal geographic regions. Its
hierarchy is incomplete as published: Bermuda, Canada, Greenland, Saint Pierre and
Miquelon, and the United States point to parent ID 918, but F01 omits that parent row.
The adapter applies one narrow repair, mapping parent 918 to Northern America and the
published Northern America region row 905. This agrees with the UN M49 composition;
all other 232 countries must follow the workbook's explicit parent chain or fail.

## Verified WUP 2018 vintage

The official WUP download center retains complete Excel archives for earlier
revisions. The registered 2018 archive contains the unchanged F22 workbook,
`POP/DB/WUP/Rev.2018/1/F22`: annual estimates through 2018 and projections through
2035 for 1,860 urban agglomerations reaching 300,000 inhabitants in 2018. The server
archive was packaged in 2025, but the workbook identifies itself, its methods and its
copyright as the 2018 revision. The archive and extracted member have separate
checksums in `data/manifest.csv`.

WUP 2018 and WUP 2025 are not the same city universe. F22 uses national
urban-agglomeration definitions and a 300,000 threshold; F21 uses harmonized DEGURBA
cities and a 50,000 reporting threshold. City codes are revision-specific. The
crosswalk therefore accepts only reciprocal nearest coordinates within the same
country, never numeric-code or name equality alone. It finds 1,710 one-to-one pairs
within 10 km, of which 1,509 have complete 2013, 2018 and 2023 populations and lie
within 5 km.

The 5 km rule is selective. It geographically matches 1,547 of the 1,860 vintage
agglomerations before later-revision outcome completeness is imposed and excludes
313. Excluded agglomerations average 2.31 million inhabitants in 2018, compared with
1.13 million among matches (standardized mean difference −0.41). Coverage also
varies substantially by country: the rule excludes 53 of 144 United States, 18 of
31 Philippine, 14 of 25 South Korean, 13 of 33 Indonesian and 8 of 15 South African
agglomerations. Twelve countries have no primary match. The coverage tables are
therefore required outputs, not incidental crosswalk diagnostics.

Among the 1,509 fully scored primary matches, country contributions range from one
city to 381 for China. The workflow therefore publishes a separate equal-country
estimate and a 141-row leave-one-country-out influence table rather than treating a
country-clustered interval as a substitute for country-balanced weighting.

Only 304 of those primary matches have 2018 populations agreeing within 10% across
revisions, and 567 agree within 20%. Population-agreement restrictions use the later
revision and are therefore sensitivity analyses, not valid 2018 selection rules.
This vintage test is informative about large-city revision bias but cannot validate
any result for cities below 300,000 or represent the full F22 large-city universe.

## Verified WUP F21 schema

The exact F21, F25, F30 and F34 workbooks were retrieved on 2026-08-27 and registered in `data/manifest.csv`. Each `Data` sheet contains 16,828 unique `City_Code` rows and annual columns from 1975 through 2050. The annual series is threshold-truncated: a cell is blank while the city is below 50,000 and populated once it meets the reporting threshold. In F21, 12,138 cities have 2025 values and 3,633 records are absent in 2025 but present by 2050. F25, F30 and F34 have identical identifiers, names, country codes and checked-year coverage, supporting joins within the WUP namespace.

F34 is a derived-variable check, but the precision varies by year. At the five-year benchmark epochs, reported density equals F21 population in persons divided by F25 land area within 0.005 persons per square kilometre. Across all annual interpolated values, differences reach 0.4 for one-square-kilometre centres because displayed population is rounded to a person while density is calculated from higher-precision inputs. The validator therefore applies a row-specific bound of 0.005 plus 0.5 person divided by reported area; all 779,718 city-years pass that bound.

F30 reports zero built-up area per capita for Timerein, Sudan, in all 46 observed years from 1975 through 2020, then positive values afterward. The adapter permits zero but rejects negative values. These records require a sensitivity flag: zero is almost certainly a missing or unresolved built-up estimate encoded numerically, not evidence that a populated city literally had no built structures.

The controlled WUP assembly produces 779,718 unique city-year rows for 16,828 cities from 1975–2050. It retains all population, land-area and density observations, derives built-up area from F21 × F30, and excludes only the 46 Timerein values from that derived measure. The maximum derived built-up share is 0.496 of land area, so no row violates the physical area bound. This assembled panel remains threshold-truncated and mixes estimates through 2025 with projections afterward; those limitations are not repaired by successful table joins.

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

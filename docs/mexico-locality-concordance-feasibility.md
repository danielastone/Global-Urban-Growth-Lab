# Mexico locality concordance feasibility

## Decision

**Feasible in principle; G2 is not yet satisfied.** INEGI publishes locality-level census
population, official geographic-key equivalence services, locality history, and census-vintage
geography. Those components support a serious concordance attempt. They do not by themselves
establish that enough of the threshold cohort can be represented on comparable geography.

The first empirical interval is **2010–2020**. Extension to 2000 is conditional on the first
interval meeting the coverage and audit rules below. This sequencing avoids mixing two
geographic transitions before the most recent transition has been measured.

## Registered empirical object

The origin cohort contains every 2010 census locality with directly enumerated population from
25,000 through 100,000. The endpoint is the directly enumerated 2020 locality population on
stable or explicitly harmonized geography. A threshold crossing occurs when origin population
is below 50,000 and endpoint population is at least 50,000. Its date is interval-censored in
the open interval `(2010, 2020)`.

Population fields and encodings must be confirmed against the acquired files before an adapter
is implemented. Expected identifiers include state, municipality and locality components, with
total population and locality name retained for audit. Expected field names are not a contract
until the exact 2010 and 2020 files have been inventoried.

## Official input families

| Input | Role | Acquisition status |
|---|---|---|
| INEGI SCITEL / ITER locality results for 2010 and 2020 | Direct endpoint population and identifiers | Official interface confirmed; exact files not acquired |
| Catálogo Único locality equivalence records | Candidate key changes and official geographic relationships | Official service confirmed; national extraction not acquired |
| Archivo Histórico de Localidades | Review evidence for locality evolution | Official interface confirmed; coverage for the cohort not measured |
| Marco Geoestadístico 2010 and 2020 | Vintage locality geometry and overlap audit | Official products confirmed; exact layers not acquired |

SCITEL exposes census and count events from 1990 through 2020 and locality identification and
total population variables. The Catálogo Único represents locality keys as nine digits: two
for state, three for municipality and four for locality. The middle component can change after
municipal reorganization, so equality of the complete key is neither necessary nor sufficient
for comparable geography.

## Concordance rules

Every origin locality receives exactly one terminal status:

1. `stable_geometry`: an official relationship and high polygon overlap support the same
   geography at both endpoints;
2. `official_crosswalk`: an official one-to-one equivalence supports a changed key and the
   geometry rule passes;
3. `harmonized_common_geography`: an explicitly documented split, merger or transfer is
   aggregated to an exact common geography using identified components and polygon unions;
4. `unresolved`: the relationship cannot be made comparable and is excluded.

For one-to-one matches, the initial geometry screen requires intersection area to cover at
least 99.5% of both endpoint polygons. The threshold is a registered pilot screen, not proof
that population definitions are identical. Retain both overlap ratios and rerun sensitivity
at less restrictive thresholds.

For many-to-one or one-to-many events, no member is accepted individually. A common-geography
record is admissible only when the official relationship identifies all components, both
endpoint population totals can be aggregated without double counting, and the polygon union
passes the registered overlap rule. Otherwise all affected records are `unresolved`.

The following are prohibited as acceptance evidence:

- repeated locality key without official relationship and geometry checks;
- locality-name equality or fuzzy name similarity;
- coordinate proximity by itself;
- interpolation of population across census years;
- treating an unresolved boundary event as demographic growth.

Names and coordinates may generate review candidates, but never determine accepted status.

## Proposed pilot acceptance gate

These thresholds are a proposal for review before the empirical run; they are not yet part of
the locked specification. G2 should pass for Mexico only if the 2010–2020 run achieves all of
the following:

- at least 90% of origin-cohort population represented on comparable geography;
- at least 85% of origin-cohort localities represented on comparable geography;
- every detected split, merger, annexation or municipality transfer resolved or explicitly
  excluded;
- zero accepted name-only or proximity-only matches;
- exact download URLs, retrieval dates and SHA-256 hashes registered for every raw input;
- a national exclusion table by state, origin size band, relationship type and reason.

Passing these conditions would establish one Global South census pilot. It would not establish
global availability or make the Mexico results representative of other national systems.

## Required outputs

The empirical pilot must produce:

- a one-row-per-origin-locality concordance with origin and endpoint keys, populations,
  relationship cardinality, match status, overlap ratios and exclusion reason;
- state-level and national count- and population-weighted coverage tables;
- a boundary-event inventory separating stable, rekeyed, harmonized and unresolved cases;
- the 25,000–100,000 cohort with the existing threshold measurement-error band;
- interval-censored crossing counts and, only after the cohort passes, comparison with WUP
  entry intervals;
- a source manifest containing exact URLs and hashes.

Skipped or unresolved records remain in the audit output. Summary statistics must never drop
them before calculating coverage.

## Manual acquisition block

1. Download the national or 32 state-level 2010 and 2020 ITER locality files from SCITEL or the
   census download pages without transformation.
2. Export the locality equivalence table, including inactive records where the official tool
   supports them, and record the service query or export settings.
3. Download the 2010 and 2020 Marco Geoestadístico locality layers and identify the exact layer
   representing the statistical locality unit used in ITER.
4. Hash and register every file before schema normalization.
5. Measure relationship cardinality and polygon coverage for the full 2010 origin cohort before
   writing an automatic acceptance rule.

Until those steps are complete, no empirical Mexico result or G2 pass may be registered.

## Official references

- [INEGI SCITEL census locality results](https://www.inegi.org.mx/app/scitel/Default?ev=9)
- [INEGI Catálogo Único web service](https://www.inegi.org.mx/servicios/catalogounico.html)
- [INEGI Archivo Histórico de Localidades](https://inegi.org.mx/app/geo2/ahl/)
- [INEGI 2020 census related materials](https://www.inegi.org.mx/rnm/index.php/catalog/632/related-materials)
- [INEGI Marco Geoestadístico 2010](https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=702825292812)
- [INEGI Marco Geoestadístico 2020](https://www.inegi.org.mx/app/biblioteca/ficha.html?upc=889463807469)

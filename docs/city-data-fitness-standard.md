# City Data Fitness Standard

## Purpose

Fitness is defined for a particular analytical use, not as a generic source score. A record can be fit for within-boundary growth estimation while being unfit for level comparisons or spatial analysis.

The standard is implemented in `urban_growth.data_fitness`. It produces explicit eligibility flags and machine-readable failure reasons without altering source values.

## Required evidence fields

The evaluator accepts the following evidence where available:

| Field | Meaning |
|---|---|
| `source_id` | Source/provenance identifier |
| `population_concept` | Administrative city, locality, municipality, agglomeration, built-up footprint, metro, etc. |
| `geographic_unit` | Declared geographic unit |
| `reference_date` | Observation reference date |
| `observation_type` | Census, estimate, projection, administrative register, etc. |
| `temporal_comparable` | Same measurement concept/method across the compared interval |
| `geographic_comparable` | Same or defensibly harmonized geography across observations |
| `boundary_temporally_fixed` | Boundary fixed over the analytical interval |
| `boundary_change_status` | None, harmonized, unresolved, annexation, merger, split, etc. |
| `administrative_reclassification` | Whether classification changed |
| `methodology_change` | Whether source methodology changed materially |
| `minimum_reporting_threshold` | Known reporting threshold, if any |
| `truncation_exposure` | none / low / material / unknown |
| `survivorship_exposure` | none / low / material / unknown |
| `concordance_method` | How geographic identity was linked through time/sources |
| `concordance_status` | stable / official_crosswalk / harmonized_common_geography / uncertain / unresolved |
| `known_inconsistency` | Known unresolved inconsistency |
| `validation_status` | passed / partial / failed / not_reviewed |
| `coordinates_validated` | Coordinates/geometries validated for spatial use |
| `network_geography_validated` | Geography suitable for network/accessibility use |

The evaluator also preserves any supplied `raw_value`, `transformation`, and `exclusion_reason` fields. It does not repair observations.

## Eligibility outputs

Each record receives four independent flags:

- `level_eligible`: suitable for population-level comparisons;
- `growth_eligible`: suitable for within-entity growth-rate analysis;
- `spatial_eligible`: suitable for spatial/network analysis;
- `headline_eligible`: suitable for headline analyses.

Each flag has a corresponding semicolon-delimited reason field. A `fitness_reasons` field contains the union of all reasons.

## Headline gate

Headline eligibility is intentionally strict. A record must be growth-eligible and must also have:

- validation status `passed`;
- a stable or accepted harmonized concordance;
- no unresolved geographic change;
- explicit truncation and survivorship exposure assessments;
- no material or unknown survivorship/truncation exposure for threshold-sensitive analyses;
- no known unresolved inconsistency.

Missing `truncation_exposure` or `survivorship_exposure` is not interpreted as low risk. Missing evidence fails headline eligibility with `missing_truncation_exposure` or `missing_survivorship_exposure`. The row may remain eligible for non-headline growth analysis when the other requirements for that use are met.

The exact analysis can impose additional requirements. The standard is a minimum gate, not permission to ignore estimator-specific assumptions.

## Geographic rules

Accepted concordance states for stable growth analysis are:

- `stable`;
- `official_crosswalk`;
- `harmonized_common_geography`.

`uncertain` and `unresolved` matches are excluded from headline analyses. They may be retained for robustness tests if explicitly requested.

A changing administrative boundary can still support growth analysis only when the observations have been harmonized to a common geography and the concordance status records that fact. A simple name match is not sufficient.

## Threshold-selection rules

For analyses near a population threshold, `truncation_exposure` and `survivorship_exposure` must be explicitly assessed and must not be `material` or `unknown` for headline use. Blank or missing values fail the headline gate rather than being treated as absence of exposure. These fields do not mechanically remove observations from unrelated analyses; they are analysis-specific warnings and gates.

Sample construction should use earlier-period population wherever possible. Entry, exit, threshold crossing, and lower-tail coverage should be reported separately.

## No composite score

Do not average these dimensions into a percentage or ordinal data-quality score. Doing so destroys the distinction between errors that invalidate levels, errors that invalidate growth, and errors that matter only for spatial analysis.

## Evidence-chain requirement

Any downstream result using the fitness flags should preserve enough identifiers to trace:

`raw source -> ingestion -> geographic concordance -> fitness evaluation -> analytical sample -> model -> robustness -> claim`.

The `headline_eligible` flag must never be manually overwritten in an analytical dataset. Change the underlying evidence and rerun the evaluator instead.

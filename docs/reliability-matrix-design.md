# Population-data reliability evidence matrix

Status: authoritative design contract for [epic #162](https://github.com/danielastone/Global-Urban-Growth-Lab/issues/162)

## Purpose

This design replaces reliance on a proprietary country-level Population Data Quality
Rating with open, versioned evidence. It does not define an "open PDQR" and it does not
authorize a universal country-quality score.

The matrix preserves distinct evidence about:

1. census foundation;
2. demographic updating;
3. statistical-system capacity;
4. estimate dependence;
5. urban comparability; and
6. the freshness and provenance of every underlying observation.

A country can be strong on one dimension and weak or unobserved on another. Downstream
analysis must select the dimensions relevant to its estimand rather than average all
available evidence.

## Non-negotiable v1 rules

- No universal A–E tiers and no cross-dimension composite score.
- Publish source fields and defensible continuous measures before derived categories.
- Preserve source observation year, release vintage, retrieval time, and lineage.
- Missing evidence is not evidence of the lowest quality.
- Conflicting assertions remain visible; a transformation may not silently choose the
  most favorable source.
- A PDQR comparison, if legally and reproducibly possible, is external concordance only.
- Gridded population products are spatial diagnostics, not independent ground truth when
  they inherit official totals or shared covariates.
- Funding or survey-pipeline disruptions are prospective risk evidence; they do not
  retroactively degrade previously collected observations.

## Relationship to existing repository contracts

This design extends rather than replaces:

- `data/sources.json`, the source-level registry;
- `data/licenses.json`, the intended-use and source-terms registry;
- `data/manifest.csv`, the acquired-artifact manifest;
- `docs/data-contract.md`, the analytical panel contract; and
- `docs/city-data-fitness-standard.md`, the analysis-specific city fitness rules.

The reliability matrix concerns evidence about national population systems and the
suitability of that evidence for specified uses. It does not overwrite city-level
geographic, temporal, or outcome fitness decisions.

## Unit and identifier rules

The default country identifier is a project-controlled `country_id`. Source identifiers
and ISO codes are retained as attributes and mapped through an evidence-bearing crosswalk.
Names alone are never join keys.

Every evidence table must state its unit explicitly. Country-level assertions use at least:

| Field | Type | Rule |
|---|---|---|
| `country_id` | string | Stable project identifier |
| `source_country_id` | string | Unmodified source identifier |
| `source_id` | string | Foreign key to `data/sources.json` |
| `snapshot_id` | string | Foreign key to a captured source artifact or response |
| `source_observation_date` | date or year | Date/year the evidence describes, not retrieval time |
| `source_release` | string | Publisher's named release or vintage |
| `retrieved_at` | UTC timestamp | When the project captured the evidence |
| `transformation_run_id` | string | Foreign key to the transformation record |

Country crosswalk failures remain in staged data and enter reporting as
`unmatched_geography`; they are not dropped from the denominator silently.

## Provenance contract

### Dataset snapshot

One row describes one immutable captured file, archived API response, or documentary
assertion package.

| Field | Required | Meaning |
|---|---:|---|
| `snapshot_id` | yes | Stable project identifier |
| `source_id` | yes | Registered source |
| `source_url` | yes | File URL, API endpoint, or evidence page |
| `retrieval_method` | yes | `file_download`, `api_capture`, or `manual_evidence` |
| `retrieved_at` | yes | UTC retrieval timestamp |
| `source_release` | yes | Named release; `not_versioned` only with an explanation |
| `source_observation_start` | no | Earliest observation represented |
| `source_observation_end` | no | Latest observation represented |
| `local_path` | yes | Project path or controlled non-committed artifact identity |
| `sha256` | yes | SHA-256 of the captured bytes or canonicalized raw response |
| `media_type` | yes | Captured artifact type |
| `license_id` | yes | Foreign key to the source-terms decision |
| `redistribution_status` | yes | Existing license-registry vocabulary |
| `capture_notes` | no | Pagination, query parameters, manual steps, or caveats |

Checksums apply to captured bytes, not to an abstract live endpoint. An API refresh creates
a new `snapshot_id`; it never overwrites the prior response.

For `manual_evidence`, the package must contain the cited page or permitted extract plus a
structured assertion record. A bare analyst claim is not a source artifact.

### Transformation run

| Field | Required | Meaning |
|---|---:|---|
| `transformation_run_id` | yes | Stable run identifier |
| `code_commit` | yes | Full Git commit SHA |
| `entry_point` | yes | Script or package function |
| `parameters_json` | yes | Canonically serialized parameters |
| `input_snapshot_ids` | yes | Ordered or canonically sorted snapshot identifiers |
| `started_at` | yes | UTC timestamp |
| `completed_at` | yes | UTC timestamp |
| `output_path` | yes | Generated table location |
| `output_sha256` | yes | Hash of the generated artifact |

An output row without a registered snapshot and transformation run fails closed.

Implementation: [#167](https://github.com/danielastone/Global-Urban-Growth-Lab/issues/167).

## Missingness and assessment-state contract

Assessment state is evaluated for one `country_id`, dimension, reference date, source
release, and declared use case. It is not a permanent country label.

Allowed states:

| State | Meaning |
|---|---|
| `scored` | Every field required for the declared dimension/use is observed and valid |
| `partially_observed` | At least one usable required field is observed, but the required set is incomplete |
| `unassessable` | No valid evidence is sufficient to assess the declared dimension/use |

Required assessment fields:

| Field | Meaning |
|---|---|
| `country_id` | Country being assessed |
| `dimension_id` | Controlled dimension identifier |
| `use_case_id` | Declared use; `descriptive_matrix_v1` is allowed |
| `reference_date` | Date at which evidence availability is assessed |
| `source_release` | Release against which completeness is evaluated |
| `expected_fields` | Canonically ordered required-field set |
| `observed_fields` | Canonically ordered valid observed-field set |
| `assessment_state` | One of the three allowed states |
| `reason_codes` | One or more machine-readable explanations |
| `transformation_run_id` | Derivation lineage |

Minimum reason vocabulary:

- `source_not_covered`
- `source_value_missing`
- `source_value_stale_for_use`
- `invalid_source_value`
- `country_crosswalk_unresolved`
- `conflicting_evidence_unresolved`
- `required_field_partial`
- `required_field_complete`

`country_crosswalk_unresolved` remains distinguishable because population-weighted
reporting assigns it to `unmatched_geography`, not to an observed quality state.

Implementation: [#169](https://github.com/danielastone/Global-Urban-Growth-Lab/issues/169).

## Dimension contracts

### Statistical-system capacity

The World Bank Statistical Performance Indicators are retained in long form. V1 selects
evidence from the data-sources, data-products, and data-infrastructure pillars, but it
does not assume that all retained indicators measure the same construct.

Required SPI fields:

| Field | Meaning |
|---|---|
| `country_id` | Mapped project country |
| `spi_economy_code` | Original economy code |
| `spi_release` | Pinned dataset release |
| `spi_observation_year` | Source observation year |
| `pillar_id` | Original pillar identifier |
| `dimension_id` | Original dimension identifier |
| `indicator_id` | Original indicator identifier where supplied |
| `value` | Unmodified numeric source value |
| `source_missing` | Explicit source missingness flag |
| `snapshot_id` | Raw-release lineage |

Before any statistical-capacity summary is proposed, report coverage, revision behavior,
pairwise correlations, and duplicated upstream sources. The overall SPI score is not a
population-reliability score.

Implementation: [#166](https://github.com/danielastone/Global-Urban-Growth-Lab/issues/166).

### Census foundation

Census evidence is event based. Recency may be calculated for a declared reference date,
but a flat `years_since_census` field is not the primary record.

#### Census event

| Field | Meaning |
|---|---|
| `census_event_id` | Stable event identifier |
| `country_id` | Project country identifier |
| `census_round` | Publisher-defined round where available |
| `census_reference_date` | Population reference date |
| `enumeration_start_date` | Fieldwork start, if applicable |
| `enumeration_end_date` | Fieldwork end, if applicable |
| `enumeration_basis` | `de_facto`, `de_jure`, `register_based`, `combined`, or `unknown` |
| `geographic_coverage` | Controlled coverage category plus source text |
| `results_status` | `planned`, `enumerated`, `preliminary`, `final`, `partial`, `unpublished`, or `unknown` |
| `post_enumeration_survey_status` | `none_reported`, `planned`, `conducted`, `published`, or `unknown` |
| `estimated_net_undercount` | Source value; never inferred from recency |
| `coverage_adjustment_applied` | `yes`, `no`, or `unknown` |
| `snapshot_id` | Assertion provenance |

Unknown is an explicit documentary state, not an invitation to infer `no`.

#### Estimate incorporation

| Field | Meaning |
|---|---|
| `country_id` | Project country identifier |
| `estimate_series` | For example, WPP or IDB |
| `estimate_vintage` | Named estimate release |
| `census_event_id` | Candidate incorporated census |
| `incorporation_status` | `incorporated`, `partially_incorporated`, `not_incorporated`, or `unknown` |
| `incorporation_method` | Publisher description; no analyst invention |
| `evidence_strength` | `explicit`, `inferred_documented`, or `unknown` |
| `snapshot_id` | Methodology or country-note evidence |

Assertions from UNSD, UNFPA, WPP, and IDB may disagree. Preserve separate source rows and
derive a resolved field only through a documented conflict policy.

Implementation: [#163](https://github.com/danielastone/Global-Urban-Growth-Lab/issues/163).

### Demographic updating

V1 may retain birth-registration completeness, death-registration completeness, and
household-survey availability as separate observations. Each value requires its own
population definition, observation year, and source vintage. Do not fill gaps by carrying
the last value forward without a separately preregistered use-specific rule.

Demographic updating is not fully implemented by the census-status issue. A bounded
implementation issue must be opened after the provenance and missingness foundations exist.

### Estimate dependence

Estimate dependence describes the evidence base and projection distance of a named
population-estimate series and vintage. It is not equivalent to census recency.

Minimum fields are `country_id`, `estimate_series`, `estimate_vintage`, `estimate_year`,
`last_direct_observation_date`, `primary_input_type`, `modeled_or_projected`,
`years_from_last_direct_observation`, `method_note_snapshot_id`, and
`transformation_run_id`.

Allowed `primary_input_type` values begin with `census`, `population_register`,
`sample_survey`, `administrative_system`, `demographic_model`, `mixed`, and `unknown`.
Publisher-specific source text must also be retained.

This dimension requires its own bounded issue; it is not silently delivered by the census
event table.

### Urban comparability

Urban comparability remains tied to stable settlement identity, definition, and boundaries.
It must reuse the repository's geographic contracts rather than convert national evidence
into a claim about locality-level fitness.

Minimum evidence includes settlement-definition version, boundary reference date, boundary
change status, locality coverage, crosswalk status, and geospatial validation status.

### Evidence freshness

Freshness is metadata attached to every observation, not an independent quality score.
Derived reporting may distinguish:

- observation age;
- publication lag;
- retrieval age;
- projection distance; and
- expected update interval.

These quantities must not be averaged across unlike source processes without a declared
use case.

## Prospective survey-pipeline risk

One row records one dated event:

| Field | Meaning |
|---|---|
| `pipeline_event_id` | Stable event identifier |
| `country_id` | Country affected; nullable only for explicitly multi-country program events |
| `program_name` | Program or survey series |
| `survey_name` | Specific survey where known |
| `planned_milestone` | Fieldwork, publication, processing, or funding milestone |
| `planned_date` | Original expected date |
| `event_type` | `cancelled`, `delayed`, `fieldwork_suspended`, `publication_halted`, `funding_ended`, `funding_restored`, or `schedule_revised` |
| `event_date` | Date the event occurred or was announced |
| `replacement_funding_status` | `none_identified`, `partial`, `full`, or `unknown` |
| `expected_next_observation` | Date/year if documented |
| `assessment_status` | `confirmed`, `provisional`, `resolved`, or `unknown` |
| `snapshot_id` | Evidence provenance |

Any current risk flag must be a deterministic function of event history and an explicit
reference date. No event changes the score of an already collected observation.

Implementation: [#168](https://github.com/danielastone/Global-Urban-Growth-Lab/issues/168).

## Separate spatial diagnostic layer

Gridded products may be compared only after documenting their upstream totals, covariates,
allocation method, vintage, resolution, and boundary semantics. Diagnostics must separate:

1. disagreement in national totals;
2. disagreement in allocation conditional on national totals;
3. settlement-omission candidates;
4. border discontinuities; and
5. disagreement among products with materially different construction.

Shared upstream inputs must be explicit. A dependent product is not an independent
replication. Stable comparison geography is required before temporal or product differences
are computed.

Implementation: [#164](https://github.com/danielastone/Global-Urban-Growth-Lab/issues/164).

## Population-weighted coverage reporting

Every report declares a population source, population vintage, reference year, universe,
and country/territory policy. For each dimension and assessment reference date, it must
reconcile:

`total population = scored + partially observed + unassessable + unmatched geography`

The output includes population totals, shares, and unweighted country counts for every
state. It also reports duplicate identifiers, missing population weights, dependencies,
and disputed-area treatment. A report that covers only matched countries may not label its
denominator as world population.

Weighting measures evidence coverage. It does not validate the evidence and it does not
authorize a cross-dimension score.

Implementation: [#170](https://github.com/danielastone/Global-Urban-Growth-Lab/issues/170).

## Post-v1 calibration and tiering gate

Tiering is prohibited in v1. A later proposal must declare exactly one downstream use case
and preregister transformations, eligible dimensions, missingness treatment, weights,
boundaries, and a sensitivity grid before inspecting downstream results.

Entry requires empirical evidence on coverage, revision behavior, redundancy, and
correlation. Preregistration documents choices; it does not by itself make arbitrary
boundaries valid.

Post-v1 issue: [#165](https://github.com/danielastone/Global-Urban-Growth-Lab/issues/165).

## Dependency and delivery order

| Order | Issue | Deliverable |
|---:|---|---|
| 1 | #167 | Provenance and vintage foundation |
| 2 | #169 | Missingness and assessment-state foundation |
| 3a | #166 | SPI vertical slice |
| 3b | #163 | Census-status vertical slice |
| 3c | #170 | Shared weighted-coverage utility |
| 4a | #168 | Prospective pipeline-risk events |
| 4b | #164 | Separate spatial diagnostics |
| post-v1 | #165 | Use-case-specific calibration/tier sensitivity |

Issues in the same numbered stage may proceed in parallel. Issue #164 additionally depends
on appropriate geographic-identity and boundary-validation contracts. Issue #165 remains
blocked until empirical coverage and correlation are known.

## Validation requirements

Each implementation PR must include, as applicable:

- schema and controlled-vocabulary validation;
- country and source-identifier uniqueness checks;
- foreign-key checks to snapshots and transformations;
- checksum format and deterministic-output tests;
- chronology checks that distinguish observation, publication, retrieval, and estimate dates;
- explicit source missingness and unresolved-crosswalk fixtures;
- denominator reconciliation for population-weighted outputs;
- revision tests showing that a new upstream vintage does not overwrite old evidence; and
- synthetic conflict cases proving that disagreement is not silently resolved.

No PR may add an empirical result without registered sources, permitted use, captured raw
artifacts or responses, reproducible transformations, and an explicit evidence-scope note.

## Downstream use map

| Downstream question | Required evidence | Evidence that is insufficient alone |
|---|---|---|
| National population comparison | Census foundation, demographic updating, estimate dependence, provenance/freshness | SPI overall score |
| Historical national panel | Vintage-specific estimate dependence, revision history, demographic updating | Current census recency |
| City-growth estimation | Urban comparability, stable geography, census/estimate lineage, city fitness | National total reliability |
| Near-50,000 threshold analysis | Locality coverage, stable identifiers/boundaries, direct-count status, selection diagnostics | Population-weighted national tier |
| Spatial allocation diagnostic | Stable comparison geography and product-dependence audit | One top-down gridded product |
| Future data-availability planning | Prospective pipeline events and expected observation gaps | Retroactive penalty to current observations |

This map is a minimum. A downstream analysis remains responsible for declaring its own
fitness gate and cannot cite the existence of the matrix as blanket approval.

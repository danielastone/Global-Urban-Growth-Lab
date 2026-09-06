# GHSL construction-lineage red-team audit

## Finding

The fixed-boundary GHSL persistence result is **not an independent replication of city-growth persistence**. It is a construction-sensitive robustness result produced from a modeled spatial population surface inside a future-defined 2025 footprint.

This distinction is separate from the already documented boundary look-ahead and future-survivor problems.

## R2023 variable-level lineage

Pesaresi et al., *Advances on the Global Human Settlement Layer by joint assessment of Earth Observation and population survey data*, shows that a dataset-level label such as `GHSL-derived` is too coarse for admissibility decisions. R2023 variables have materially different observation and model structures.

| Variable / operation | Construction | Consequence |
|---|---|---|
| GHS-BUILT-S | multitemporal EO/modelled built surface | sensor/model-era sensitivity remains relevant |
| GHS-BUILT-H | 2018 EO/DEM height layer | not a historical height panel |
| GHS-BUILT-V | multitemporal built surface combined with temporally fixed 2018 height structure within each 100 m sample | historical volume change is not observed vertical construction |
| GHS-BUILT-V-NRES / residential volume | volume plus RES/NRES classification whose within-sample share is assumed constant through time | historical land-use conversion is not directly observed |
| GHS-POP aggregate controls | census/GPW trajectory plus UN controls | R2023 trajectories are rescaled to WUP 2018 city and WPP 2022 country controls; totals are not independent of those controls |
| GHS-POP spatial allocation | controlled population plus residential built volume | EO informs intra-unit placement, not an independent city population total |

The dependency asserted here is one-directional: R2023 GHS-POP uses UN population controls. This audit does **not** infer that WUP or WPP use GHS-POP from that fact.

## Aggregate-total calibration versus spatial disaggregation

The population lineage must be split into two stages rather than described generically as population inferred from built form. GHS-POP first constructs census-based trajectories using GPWv4.11 information and applies UN controls, including WUP 2018 at city level and WPP 2022 at country level. It then spatially downscales the resulting population using residential built-up volume.

Residential built volume therefore affects the intra-unit allocation but should not be described as determining an independent city-level total. A WUP-controlled GHS-POP city total is not independent validation of a WUP-derived outcome. A nominal historical epoch can also embed later source information: a value represented as year `t < 2018` is not automatically information available at forecast origin `t`. See #201 for the hard point-in-time and independence gates.

The WUP calibration carries a separate geography-definition layer: the R2023 procedure approximates WUP cities using point locations and merged administrative units rather than starting from an authoritative WUP city polygon. Aggregate-control lineage and boundary lineage must remain separately visible.

## Built-form temporal constraints

### Height and volume

GHS-BUILT-H R2023 is a 2018 height snapshot. The multitemporal volume construction assumes average building height in a 100 m sample remains constant over time. Historical or forward GHS-BUILT-V change therefore must not be interpreted as directly observed vertical growth. Repository variables such as `volume_per_surface` may be useful as level covariates where admissible, but they are not evidence of observed vertical change through time.

### Residential/non-residential backcasting

R2023 also assumes the residential/non-residential share within a 100 m sample remains constant over time when deriving multitemporal residential/non-residential volume. Historical residential volume therefore does not independently observe industrial-to-residential conversion, changing mixed use, or similar land-use transitions. Density and allocation analyses using residential volume must preserve this static-share assumption in lineage metadata.

### 2025 and 2030 modeled built form

The paper describes 2025 and 2030 GHS-BUILT-S/V values as MT_B model predictions. They must not be silently treated as observed EO outcomes or origin-available covariates. Forecast evaluation requires explicit observed-versus-modeled status and information-vintage gates for these epochs.

## Sensor/model-era comparability

The paper documents a motivation for redesigning the multitemporal built-up method: differing satellite sensitivity to scattered settlements could otherwise create spurious apparent change. R2023 is designed to improve consistency, so this is **not** evidence that R2023 necessarily retains a discontinuity. It establishes sensor/model-era comparability as a risk requiring empirical sensitivity analysis rather than an assumption of seamless physical measurement.

This is particularly relevant to small-city expansion and sprawl, where peripheral/scattered construction can carry substantial signal. Built-up-growth results should be tested for sensor/model-era dependence before promotion to headline evidence.

## Population temporal smoothing beyond spatial allocation

The R2023 population trajectory construction contains temporal controls in addition to WUP/WPP rescaling. The paper describes convergence toward upper administrative-level trajectories at historical/forward edges and toward country-level WPP growth over long horizons. These controls can suppress or reshape local volatility independently of the 100 m spatial allocator.

GHS-POP therefore should not by itself establish the magnitude of local mean reversion, persistence, conditional volatility, rank volatility, or tail behavior. Direct locality census counts with defensible longitudinal concordances remain the preferred falsification source.

## Census-support modification

Before population downscaling, R2023 uses EO information to revise aspects of census support, including coastline and nominally unpopulated-unit handling. A GHS-POP census support is therefore not necessarily identical to untouched official census geography. Claims of independent direct-census validation should use official census support or another independently justified geography rather than treating GHSL-adjusted support as the independent benchmark.

## Mechanical density relationships

R2023 uses linear dasymetric mapping in which population is spatially allocated in proportion to residential built-up volume. Relationships between GHS-POP-derived density measures and residential built volume therefore have a direct construction channel. A generic `shared GHSL lineage` warning is insufficient: the registry should identify when a denominator or covariate participates directly in the population allocator.

Such measures can remain descriptive or sensitivity measures, but they cannot independently demonstrate a population-built-form relationship imposed by the allocation rule itself.

## Validation scope

The paper's population validation evaluates spatial disaggregation against independent gridded census information across heterogeneous national census supports. It validates the allocation step, not independence of the WUP/WPP-controlled aggregate total and not temporal forecast validity of historical city growth.

Aggregate allocation-accuracy results therefore must not be imported as a universal reliability score for the project's roughly 50,000-population city cohort. Validation should be stratified where possible by city size, density, census-support granularity, geography and relevant forecast epoch.

## Evidence already inside this repository

The matched fixed-versus-dynamic GHSL sensitivity shows construction choices materially affect apparent persistence:

- fixed-2025-footprint persistence MAE: 0.758 percentage points;
- dynamic-footprint persistence MAE: 1.274 percentage points;
- fixed-2025-footprint persistence RMSE: 1.334 percentage points;
- dynamic-footprint persistence RMSE: 2.268 percentage points;
- 2020 within-country recent/future correlation: 0.764 fixed versus 0.532 dynamic.

Holding the footprint fixed makes the same source family substantially smoother and persistence stronger. This does not prove population disaggregation is the cause; it demonstrates sensitivity to the source-construction package.

Subsequent repository red-team work weakens a simple allocator-smoothing explanation: residualizing fixed-footprint population growth on built-up growth did not materially remove persistence, and the Japan direct-count comparison did not show GHS-POP persistence consistently exceeding direct census persistence. The remaining concern is broader source construction, information vintage, geography and temporal controls—not a claim that the 100 m allocator alone explains H1.

## What can and cannot be concluded

Allowed interpretation:

> Within the retrospective GHSL modeled population surface, recent growth remains highly predictive when population is measured repeatedly inside the same 2025 urban-centre footprint.

Not allowed:

- GHSL independently confirms the real-world magnitude of city-growth persistence;
- a WUP-controlled GHS-POP city total independently validates a WUP persistence coefficient;
- nominal historical GHS-POP epochs are automatically point-in-time observations available at those epochs;
- historical GHS-BUILT-V identifies observed vertical growth;
- historical residential volume independently observes changing RES/NRES land use;
- the fixed-boundary result identifies how much persistence is demographic rather than source-construction or footprint induced;
- stronger fixed-footprint persistence proves changing boundaries caused the WUP/GHSL disagreement;
- spatial-allocation validation establishes temporal forecast validity.

## Required falsification and governance

For population, the preferred falsification is an external direct-count benchmark, not another GHSL transformation. Define the origin cohort before concordance exclusions; estimate growth from direct counts; compare GHSL only on matched locality-period samples while preserving source vintage; and stratify by census recency, concordance quality and relevant city-size/density classes. Materially different GHSL behavior is a construction/vintage diagnostic, not automatically proof that either source is correct.

For built-form predictors, separately test sensor/model-era stability and prohibit modeled 2025/2030 values from masquerading as observations.

## Claim status

This audit does not invalidate registered GHSL numerical outputs. It changes their evidentiary role. Existing outputs remain reproducible retrospective diagnostics, but they cannot upgrade a persistence, volatility, density or vertical-growth claim beyond what direct-count, direct-observation or vintage-correct evidence supports.

Related: #27, #124, #130, #201.

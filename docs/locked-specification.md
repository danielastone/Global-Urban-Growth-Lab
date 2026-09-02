# Locked empirical specification

Status: implementation contract adopted 29 August 2026. The architecture is locked;
named feasibility gates remain open. This file governs code behavior when older design
notes are less specific.

## Module architecture

| Module | Empirical object | Role |
|---|---|---|
| A — national envelope | National population by settlement class | Directly measure allocation to cities, towns and rural areas. |
| B — within-country allocation | City growth conditional on country-period | Estimate which observed cities capture growth; country-by-period effects absorb the national envelope. |
| C — urban form | Horizontal extent, density and cautiously used vertical measures | Test contemporaneous association and both lead-lag directions separately. |
| D — accessibility | Modern travel-time rival mass | Validate spatial structure only for supported modern vintages; never backcast a 1975–2025 travel-time panel. |
| E — census threshold | Locality census cohorts around 50,000 | Audit WUP entry, survivorship and threshold measurement; do not treat this as an RDD. |

Modules A and B are linked but not a literal single regression. Module A uses national
settlement-class observations. In retrospective Module B, country-by-period fixed effects
absorb every national variable common to cities in that cell. A recovered-fixed-effect
decomposition is diagnostic only and excludes sparse country-period cells.

## Outcomes and timing

City growth is annualized log growth over an exact interval. `decline_any` is growth below
zero; `decline_material` is growth below -0.005 annually. Continuous origin population and
rank are primary. Presentation tiers and ILR membership are fixed at the forecast origin.
Endpoint rank, realized tier and future urban form cannot enter a forecast-origin model.

The form module has three distinct specifications:

- **C1:** population growth and form change measured over the same interval; association only.
- **C2:** population growth over the preceding interval predicts later form change.
- **C3:** form change over the preceding interval predicts later population growth.

If C2 and C3 both predict, report joint dynamic adjustment rather than selecting a one-way
causal story.

### Module C density and form extension

Module C uses fixed, validated polygons. F01 Cities-class change is not a density outcome:
it mixes in-place change with territory entering or leaving the class. Density metrics must
identify the numerator, denominator, spatial support, reference date, availability date and
lineage in a versioned metric registry before use. Lineage is enforced for the
predictor/outcome pair: `clean` for a built-form metric means clean against a registered
direct-count outcome on enumerated support, not globally clean. Pairing the same metric with a
GHS-POP- or WUP-based outcome is sensitivity-only.

Any metric pairing GHS-POP, or GHS-POP-based WUP, with GHS-BUILT is
`lineage_entangled` because the population surface inherits built-layer allocation. Such a
metric is sensitivity-only and cannot validate the built layer or serve as the primary density
outcome. A census count is an independent numerator only on its enumerated support. If census
units are allocated into an analysis polygon, the allocation method, overlap coverage and
uncertainty are explicit; the resulting polygon estimate is not described as direct enumeration.

GHS-BUILT-H is a 2018 snapshot. Historical GHS-BUILT-V epochs combine changing built
surface with that snapshot height and therefore do not observe multi-epoch vertical change.
They may describe constructed volume under the tag `snapshot_height_scaled_surface`, but
vertical-growth language requires an independent multi-date height or floor-space source.
The registered decomposition reports horizontal extent change, within-common-support vertical
change, entering-cell composition and an interaction or residual separately.

Every C3 form or density feature carries `source_date` and `available_from`. The 2018 snapshot
height is unavailable to forecast origins before 2020. Feature selection, tuning and practical
improvement thresholds are fixed without later-origin outcomes. The primary test compares
origin-available features against the contemporaneous-country baseline on a registered
direct-count density outcome; persistence is also reported where applicable. Shared-lineage
reconciliation is an accounting check or sensitivity, not external validation.

Measurement epoch and public availability are separate clocks. Retrospective measurement tests
may use a time-indexed observation at its measurement epoch but must not call it real-time or
vintage-correct when the product was released later. Google Open Buildings Temporal is measured
annually from 2016–2023 (level from 2016; first change from 2017) but is publicly available only
from 2024. Copernicus DEM slope may be backcast as a registered time-invariant physical
constraint in retrospective tests while retaining its actual public-availability date.

`volume_per_surface` from GHSL snapshot-height-scaled epochs is a spatial level only. It is not
an admissible change outcome or a measure of vertical growth.

### Open-covariate density model pre-registration

No empirical density-model run may precede this registration or use a covariate absent from
`density_covariate_registry()`. The primary change outcome is annualized log direct-census
density change on validated fixed polygons; the cross-sectional outcome is log direct-census
density. Log GHS-POP density change is lineage-entangled and sensitivity-only.

The comparator ladder is density persistence, contemporaneous-country density mean, and a
national-envelope-only comparator. The WUP-based national envelope is a comparator, not an
admissible lineage-clean covariate. Candidate models are restricted to registered built-form,
terrain/constrained-land, accessibility and independent-height features available at the
origin. VIIRS night lights is sensitivity-only. GHS-POP, WUP city population, and variables
derived from either are excluded from the candidate covariate matrix.

Evaluation holds out pilot cities and uses a stratified state/entidad cluster bootstrap within
country. With only Mexico and the United States, inference is limited to pilot regions and
cannot support country-generalized or global uncertainty claims. The primary paired contrast is
relative RMSE improvement over the contemporaneous-country model. The model passes only when
the lower bound of its registered 95% interval is at least 5% and its MAE is no worse on
identical rows.
Otherwise the required conclusion is **“open-data density model not supported.”** Favourable
and adverse model rows remain in the same registered result table.

A caller boolean does not register an outcome. Before fitting, the code verifies the direct-count
outcome's expected-output manifest, checksum, metric id, census vintage and enumerated spatial
support. Adding a covariate after outcomes are inspected requires a new dated registration and
cannot revise the original test.

## Module B model and estimator hierarchy

The general retrospective template is:

```text
g_ict = alpha_ct + mu_i + rho g_ic,t-1 + beta' X_ic,t-1 + epsilon_ict
```

This is a template, not one fitted “primary” estimator. Active terms depend on the row below.

| Tier | Specification | Purpose and limitation |
|---|---|---|
| 1 | Pooled dynamic model; omit `mu_i` | Primary predictive benchmark. It retains stable between-city signal and does not identify a within-city effect. |
| 2 | City fixed effects; include `mu_i` | Within-city diagnostic. With a lagged outcome and short panels it is Nickell-biased. |
| 3 | Finite-T bias-corrected city-FE dynamic model | Primary retrospective within-city estimate when implementation and simulation gates pass. |
| 4 | Restricted dynamic GMM sensitivity | Use only with collapsed, limited instruments and explicit weak-instrument/proliferation diagnostics. |

Run the first three on the same analytic sample. If conclusions disagree, report the
disagreement. Do not choose the estimator that produces the preferred sign. Standard errors
must account for country clustering and period dependence; add spatial diagnostics before
claiming conventional inference is adequate.

## Composition and settlement hierarchy

Do not regress raw city shares as independent outcomes. The primary city-growth model uses
country-by-period effects. Secondary compositional analysis uses ordered, fixed-tier ILR
balances. Per-city leave-one-out share denominators are prohibited because they are unstable
in primate systems.

Absolute size and relative hierarchy are parallel classifications answering different
questions. Absolute thresholds require a staleness audit; relative tiers are rank/count based,
not defined by fixed population shares. Tier transitions are reported separately from growth
within forecast-origin membership.

## Census threshold audit

The master cohort contains localities with origin population from 25,000 through 100,000,
observed at two endpoints on stable or explicitly harmonized geography. It separately records:

1. census crossing of 50,000;
2. WUP entry;
3. WUP exit;
4. relative-hierarchy tier movement.

Crossing and entry are interval-censored. If crossing is in `(t0, t1)` and entry is in
`(w0, w1)`, delay is in the open interval `(w0 - t1, w1 - t0)`. Do not substitute an
interpolated point year as observed fact. Run threshold-error sensitivity bands and distinguish
direct enumeration from interpolation or projection.

The audit sample and ILR sample may originate from the same census records but have different
eligibility filters. The audit requires comparable endpoints; the ILR requires positive cells
in every tier entering a balance. Never silently force one sample to equal the other.

## Geography and lineage

Population and form are measured on fixed, validated polygons within an analysis. Boundary
events are logged; changing polygons are never represented as demographic growth. Baseline
form is admissible as a predictor only when available at the origin. Variables derived from the
population outcome or sharing built-up disaggregation inputs are tagged as lineage-entangled
and cannot be described as independent confirmation.

For precision: the 1975–2020 historical GHS-WUP population is informed by GHS-BUILT-V or
related built layers; CRISP proper applies to the 2025–2100 projection workflow. The substantive
lineage warning applies across the historical and projection windows even though the workflow
names differ.

## Accessibility

Travel-time bands are mutually exclusive: `[0,1)`, `[1,2)`, `[2,4)` and `[4,8)` hours. Rival
mass excludes the focal city. The 2015 MAP layer and later friction surfaces are modern-period
validation data, not a historical series. Enter nested spatial constructs rather than five
collinear variants simultaneously: geography and hierarchy; one registered market-potential
or rival-mass construct; mutually exclusive bands; then dominance or fragmentation, one at a
time.

Positive spatial coefficients can reflect agglomeration or common location advantages;
negative coefficients can reflect competition or congestion. Sign alone does not identify the
mechanism.

## Prediction and reporting

Use chronological rolling origins, frozen candidate models, an untouched later vintage when
available, and leave-country-out diagnostics. Report MAE, RMSE, median absolute error, bias,
directional accuracy, calibrated intervals and coverage by size, geography and data quality.
The inspected 2020 outcome is development evidence, not a pristine holdout.

Claims must be labeled descriptive, predictive, temporal or causal. Current permitted language
is that recent growth is the strongest reproducible predictor in the observed panel and initial
size is associated with decline incidence. “Size protects cities” and “nearby cities compete for
a fixed pool” are prohibited without separate identification.

## Automated gates

Code must fail on duplicate keys, nonpositive population, future leakage, endpoint-derived tier
membership, cumulative travel-time bands, unresolved census geography, absent census endpoints,
empty ILR cells represented as zero, lineage-undisclosed form variables, primary use of a
`lineage_entangled` density metric, pre-availability C3 features, and claims of vertical change
from snapshot-height-scaled surface epochs. Every exclusion receives a machine-readable reason.

## Feasibility register

| ID | Issue | Required output |
|---|---|---|
| O1 | Mexico locality concordance | Run 2010–2020 first using official equivalence records and vintage geometry; extend to 2000 only after the first transition passes coverage review |
| O2 | Brazil census-sector harmonization | Crosswalk coverage table |
| O3 | South Africa and Ghana multiwave access | Access and coverage memo |
| O4 | Absolute and relative tier definitions | Versioned tier registry |
| O5 | Finite-T bias correction | Estimator simulation |
| O6 | Spatial dependence | Inference memo |
| O7 | Independent morphology pairing | Lineage validation matrix |
| O8 | Modern accessibility window | Accessibility protocol |
| O9 | Forecastable national envelope | Separate forecast-module specification |
| O10 | India census scope | Test 2001–2011 as historical-only; defer modern validation until Census 2027 locality outputs and crosswave concordances exist |
| O11 | U.S. Census place pipeline | Validate code on direct 2010/2020 enumerations and official one-to-one boundary relationships; does not close O1–O3 |
| O12 | Density and vertical-form extension | Complete #145: register a direct-count density outcome, acquire an independent multi-date height source, and test origin-valid C3 improvement |

No shrinkage model can manufacture missing within-country information. The recovered
country-period effect diagnostic excludes cells with fewer than three eligible cities and
reports the city count and uncertainty; direct national settlement-class data remain the
primary national-envelope analysis.

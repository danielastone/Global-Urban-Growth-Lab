# H5 internal accessibility control — preregistration

Status: **preregistered computational specification**. The computational architecture and routing-support gates are frozen before empirical routing or inspection of city-growth outcomes. Empirical activation remains blocked pending exact OSM source/vintage acquisition, engine/profile registration, source/license governance, and outcome-blind routing-quality assessment.

Related: #142, #157, #161, #203, #205, #206, PR #207.

## Purpose

Control explicitly for focal-city internal accessibility so H5 domestic/foreign rival-mass coefficients do not absorb within-city form, sprawl, or egress friction. Internal accessibility is treated as a focal-city attribute, separate from pairwise intercity accessibility.

Primary H5 interpretation remains: physically accessible rival population across versus within borders, conditional on focal-city internal accessibility and other preregistered controls.

## Primary estimator

Let `g` index population grid cells inside city `i`, `P_g` denote gridded population, and `A_i` denote the city's algorithmic set of eligible intercity-network gateway nodes. For each grid cell, compute minimum routed time to any eligible gateway:

`T_gAi = min_{a in A_i} T(g -> a)`.

Primary internal-accessibility summaries are population-weighted:

- mean travel time;
- median travel time;
- P90 travel time;
- `Share30`: share of city population with modeled travel time greater than 30 minutes.

Preregistered tail sensitivities are `Share15` and `Share45`. These thresholds may not be changed after growth outcomes are inspected.

## Gateway set A_i

Primary eligible road classes are OpenStreetMap `motorway`, `trunk`, and `primary`, including corresponding `_link` variants.

`A_i` contains all routable nodes on those eligible classes located within the urban footprint plus a fixed **5 km buffer**. There is no analyst-selected minimum or maximum gateway count.

If no eligible gateway node exists within the footprint plus 5 km, the primary metric is unavailable. It must not be replaced by an arbitrarily large travel time.

Adding `secondary` roads is a preregistered sensitivity only.

Directional egress toward a specific rival city is a sensitivity analysis only. It is not the primary `InternalAccess_i` measure because pair-specific egress would contaminate the focal-city control with external-exposure direction.

### Urban-footprint rule (R1 closed)

The primary footprint is the repository-registered **GHS Urban Centre Database R2024A v1.2** source, `source_id = ec_ghsl_ucdb_r2024a_v1_2`, using the **fixed 2025 urban-centre boundary stream** from `GHS_UCDB_THEME_GHSL_GLOBE_R2024A_V1_2.zip`. This is the same fixed-polygon semantics used by Module C for comparable within-city aggregation; the multi-temporal `MTUC` geometry stream is not substituted into the primary InternalAccess measure.

Population cells used in `InternalAccess_i`, gateway eligibility, snap-coverage denominators, and Module C joint diagnostics must all reference that same fixed polygon for a city. City identity still comes from the project concordance rather than OSM place nodes.

Because the fixed 2025 polygon is not an origin-available boundary for pre-2025 forecasting, InternalAccess computed on this footprint is a **standardized modern validation/control measure**, not an origin-available historical predictor. Any forecast-origin use before 2025 requires a separately preregistered, origin-available boundary treatment and may not silently reuse the fixed-2025 footprint.

## Rival-side access

Rival-city internal access `T_j^access` is excluded from the primary rival-mass travel-time decay/bands. Primary H5 pairwise accessibility is gateway-to-gateway physical road-network travel time.

Rival-side access may enter only through a separately labeled sensitivity, such as an access-adjusted rival-population weight or rival-city attribute. It may not silently alter the primary domestic/foreign rival-mass estimand.

## Source and temporal contract

Historical OSM routing is the primary measurement source. Weiss/MAP accessibility may be used only as validation/sensitivity context, not as an intra-urban ground-truth measure.

Internal and intercity routing must use the same primary network specification:

- same OSM snapshot vintage;
- same geographic build/extract lineage;
- same routing-engine version;
- same routing profile;
- same speed defaults;
- same ferry policy;
- same snapping rules.

Any deliberate divergence belongs in a separately labeled sensitivity and must state why the sources differ.

A later road network is never carried backward to an earlier growth period. Unsupported city-rounds remain in the underlying city panel but receive `internal_access_status = vintage_unavailable` and are excluded only from specifications requiring InternalAccess.

### Vintage tolerance (R2 closed)

The primary OSM snapshot must be dated **no more than 12 months before** the accessibility reference date and may not post-date that reference date. Formally, an admissible snapshot satisfies:

`0 <= reference_date - osm_snapshot_date <= 365 days`.

If no otherwise admissible snapshot exists within that window, the city-round receives `internal_access_status = vintage_unavailable`. The tolerance is global and may not be relaxed for individual cities after inspecting routing or growth outcomes. Alternative wider windows, if later studied, are sensitivity analyses and must be labeled as such.

## Routing-support adequacy

Primary maximum population-cell snap distance is **2 km**.

Define population-weighted snap coverage as:

`SnapCoverage_i = population successfully snapped within 2 km / total gridded population in city i`.

Primary InternalAccess requires `SnapCoverage_i >= 0.90`.

Define conditional gateway-connected coverage as:

`GatewayConnected_i = population among successfully snapped cells whose snapped nodes lie in a graph component containing at least one eligible gateway / population successfully snapped within 2 km`.

### Connectivity gate (R3 closed)

Primary InternalAccess requires **`GatewayConnected_i >= 0.95`** in addition to the 90% snap-coverage gate. The two gates are evaluated separately and both must pass. This prevents a city with nominally successful snapping but a fragmented routing graph from being treated as having a valid internal-accessibility estimate.

A city failing either required routing-support gate receives `internal_access_status = insufficient_routing_support` rather than a high travel-time value.

**Measurement unavailable is not measured low accessibility. A sparse OSM network must never be interpreted as evidence of poor internal connectivity.**

Do not label low road density or poor routing support as "OSM incompleteness" unless an independent external benchmark actually supports a completeness assessment.

## Measurement semantics and caveat

InternalAccess is a modeled road-network accessibility proxy, not observed commuting or urban travel time. It does not observe congestion, transit schedules, mode availability, vehicle ownership, waiting, or other behavioral frictions.

The Weiss/MAP friction surface is approximately kilometre-scale and designed for global accessibility-to-cities rather than intra-urban circulation; it may inform sensitivity/validation but must not be presented as observed internal travel time.

## Relationship to Module C

Built-up extent, density, and InternalAccess are related but not interchangeable. Joint specifications must diagnose collinearity and emphasize incremental out-of-sample predictive value rather than over-interpreting individual coefficients when predictors are strongly correlated.

## Missingness states

At minimum retain distinct states for:

- `measured`;
- `vintage_unavailable`;
- `no_eligible_gateway`;
- `insufficient_routing_support`;
- `route_failure` or equivalent graph/routing failure.

These states may not be collapsed into high accessibility cost.

## Empirical activation gate

The computational specification is preregistered, but empirical H5 use remains blocked until:

1. exact OSM source, vintage, checksum, engine, and profile are registered;
2. source/license governance is resolved;
3. routing-support adequacy is evaluated outcome-blind under the frozen 90% snap and 95% conditional-connectivity gates;
4. no growth outcomes have influenced network/profile/gateway choices;
5. any pre-2025 forecast-origin application uses a separately preregistered origin-available city-boundary treatment rather than the fixed-2025 UCDB polygon.

Only after those conditions are met may InternalAccess enter H5 empirical specifications.

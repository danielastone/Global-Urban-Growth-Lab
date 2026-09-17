# H5 internal accessibility control — draft preregistration

Status: **draft preregistration**. The computational architecture is fixed in principle, but empirical activation remains blocked pending OSM source/vintage acquisition and routing-quality assessment. Three residual specification TODOs (R1–R3) must be closed before preregistration is complete.

Related: #157, #203, #205, #206, PR #207.

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

**TODO R1 — urban footprint pointer:** link this definition to the exact project city-boundary/urban-footprint layer already used by the city concordance and spatial modules. Internal-accessibility cells, gateway selection, and H5 rival-mass city extents must use the same city-extent semantics unless an explicitly preregistered sensitivity says otherwise.

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

**TODO R2 — vintage tolerance:** set the maximum allowed lag between the accessibility reference date and the admissible OSM snapshot. The rule must be numeric and applied identically across cities before empirical routing.

## Routing-support adequacy

Primary maximum population-cell snap distance is **2 km**.

Define population-weighted snap coverage as:

`SnapCoverage_i = population successfully snapped within 2 km / total gridded population in city i`.

Primary InternalAccess requires `SnapCoverage_i >= 0.90`.

Also report the fraction of successfully snapped population connected to a graph component containing at least one eligible gateway node.

**TODO R3 — connectivity gate:** either set a numeric minimum connected-population fraction for primary acceptance or state explicitly that the connectivity statistic is informational only. This choice must be frozen before empirical routing.

A city failing a required routing-support gate receives `internal_access_status = insufficient_routing_support` rather than a high travel-time value.

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

This draft may be implemented with synthetic tests now. Empirical H5 use remains blocked until:

1. R1–R3 are closed;
2. exact OSM source, vintage, checksum, engine, and profile are registered;
3. source/license governance is resolved;
4. routing-support adequacy is evaluated outcome-blind;
5. no growth outcomes have influenced network/profile/gateway choices.

Only after those conditions are met may InternalAccess enter H5 empirical specifications.

# H5 historical OSM border-neutral routing pilot — preregistration

Status: **method-selection preregistration; no city-growth outcomes may be inspected for this pilot before the routing/validation decision is frozen.**

Parent issues: #205, #206. Related: #31, #157, #203.

## Purpose

Test whether a reproducible historical OpenStreetMap road-network measure can provide the border-neutral physical-accessibility input required by H5. This is not a reproduction of the MAP multimodal friction surface and is not a causal border design.

## Pilot geographies

The pilot is fixed before growth outcomes are inspected:

1. **Germany–Czechia**: high-connectivity European land-border corridor.
2. **Mexico–Guatemala**: non-European land-border corridor with substantially different network density and mapping conditions.

For each corridor, include domestic comparison pairs drawn from the same country-side border regions at comparable straight-line distance. Pair selection may use geography, city size, and network feasibility only; it may not use observed or forecast city-growth outcomes.

A continent-scale or merged extract must be used where necessary so source clipping does not mechanically sever cross-border roads.

## City and pair contract

- City identity comes from the project's existing city concordance, not OSM place nodes.
- Representative point: project city centroid/representative point already used by spatial modules; if multiple definitions exist, freeze one before routing.
- Directed focal-rival pairs; self-pairs prohibited.
- Maximum routing horizon: **8 hours**, matching the existing H5 accessibility bands.
- Maximum allowed snap distance: **2,000 m** for the primary pilot. Sensitivity at 1,000 m and 5,000 m may be reported, but the primary rule cannot change after outcome inspection.
- Route failures and graph-disconnected pairs remain explicit validation failures; they are not assigned large synthetic travel times.

## Border-neutrality rule

The routing graph must not add any cost, delay, restriction, or penalty solely because an edge crosses an international boundary. Real road attributes present in OSM may affect routing, but country identity itself may not alter generalized cost in the primary H5 route.

`border_penalty_applied` must be `False` for every primary routed pair accepted into exposure construction.

## Routing profile

Use an open reproducible motor-vehicle routing engine and a pinned profile. Engine version, profile hash, allowed highway classes, speed defaults, ferries, toll/restricted roads, and third-country routing must be committed before any growth regression is run.

Until those fields are pinned, the pilot may generate synthetic/contract tests only and may not create empirical H5 results.

## Source vintage

Target a **2019-01-01 historical OSM snapshot** when an appropriate Geofabrik historical extract exists. If the exact geography/date is unavailable, the replacement vintage must be documented and approved before routing; it must not be selected based on growth results. The resulting variable is named by its actual OSM snapshot vintage, not "MAP 2015".

## Validation

Before any H5 growth model:

- compare an outcome-blind preregistered sample of away-from-border pairs with an external travel-time benchmark;
- report MAE, median absolute error, mean signed error/bias, and rank correlation;
- report route success and snap-distance distributions separately for domestic and cross-border pairs;
- verify no cost discontinuity is introduced merely by international-border crossing;
- run hard-band and continuous/smoothed exposure constructions on the same accepted route table;
- report sensitivity to reasonable routing-profile speed defaults.

No single accuracy threshold is claimed in advance because a defensible external benchmark/sample has not yet been acquired. The go/no-go decision must therefore be documented before growth outcomes are inspected and must compare cross-border failure/snap behavior with domestic controls rather than accepting differential missingness silently.

## Output semantics

The pilot output is a modeled **road-network accessibility** measure. It excludes rail, navigable water, off-road walking, congestion, schedules, and other MAP friction components. It is a predictive exposure covariate only; coefficient signs do not identify competition, agglomeration, or causal border effects.

# H5 border-neutral accessibility requirement

H5 asks whether national borders condition spatial spillovers beyond distance and physical accessibility.

## Source constraint

Weiss et al. (2018) construct the nominal-2015 friction surface from roads, rail, rivers, water, land cover, terrain and national borders. Border penalties are imposed inside the friction surface with priority over other layers. The published implementation uses a static one-hour crossing penalty outside Schengen and the UK-Ireland common zone because globally consistent crossing-time data were unavailable.

The current Malaria Atlas Project resource page exposes direct downloads for both the travel-time-to-cities raster and the associated friction surface. MAP's current open-access policy states that its maps are available under CC BY 3.0 Unported with citation.

## Identification consequence

The published MAP surface cannot be the primary H5 exposure. Using a border-penalized travel-time surface and then testing whether cross-border rival mass is weaker would partly recover an upstream modeling assumption.

The primary H5 exposure must use **border-neutral physical travel time**. Rival population is split into same-country and cross-border mass only after physical travel time is computed:

`M_ib = M_ib_same_country + M_ib_cross_border`

The substantive H5 contrast is the difference between the predictive contribution of same-country and cross-border physically accessible rival mass conditional on the baseline geography/accessibility model. Coefficient sign alone does not identify competition or agglomeration.

## Why the released friction surface cannot simply be corrected

Because the border rule is imposed within friction construction, the released raster does not preserve the counterfactual border-free cost at those cells. Subtracting one hour from cross-border paths is not an equivalent reconstruction: removing the penalty can change the least-cost route itself.

Rebuilding the original 2015 surface without borders also has a lineage constraint because the paper merged OSM roads with a Google roads-derived layer; the historical Google component is not a reproducible open input in this repository.

## Empirical activation gate

H5 remains blocked until one of these is preregistered and implemented:

1. a separately sourced border-neutral physical friction surface with acceptable vintage, licensing and reproducibility;
2. an open reconstruction from pinned transport/terrain inputs, validated against MAP or another benchmark, with the estimand explicitly defined to that reconstruction; or
3. a different border-discontinuity design that does not condition on a border-penalized accessibility raster.

The MAP border-penalized surface may remain as a sensitivity specification only.

Related: #31, #157, #203.

This document is a design constraint, not an empirical result.

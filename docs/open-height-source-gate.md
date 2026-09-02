# Independent height-source gate and first pilot

## Fitness decisions

| Source | Inputs and lineage | Epochs / coverage | Fitness verdict |
|---|---|---|---|
| Google Open Buildings 2.5D Temporal v1 | Sentinel-2 optical imagery and model predictions; no population or GHSL built allocation input | Annual 2016–2023; Africa, South/Southeast Asia, Latin America and Caribbean; 4 m effective resolution (0.5 m release grid) | **Pass for independent multi-date height pilot**, subject to presence-threshold, cloud, alignment and model-error sensitivities. |
| DLR WSF3D v2 | Sentinel-1/2, TanDEM-X/digital elevation and settlement processing; no population allocation input | Global, 90 m, approximately 2019 single snapshot | **Cross-validation only**; independent height snapshot but not vertical change. |
| Microsoft Global Building Footprints | Maxar, Vexcel, Airbus and other imagery; no population input; acquisition dates vary and height coverage is sparse | Global footprint mosaic, imagery roughly 2014–2025; height only where available | **Horizontal/snapshot sensitivity only**; not a spatially uniform time series. |
| Overture Buildings | Conflation of multiple providers including OSM and machine-derived footprints; height provenance and completeness vary | Current releases, global, no stable annual historical panel | **Horizontal/snapshot sensitivity only**; release changes are not building change. |

Google's official catalog states that building presence is uncalibrated and can vary with cloud
cover and imagery alignment. The pilot therefore reports thresholds 0.3, 0.5 and 0.7 rather
than selecting a favorable cutoff after seeing results.

## GHSL premise test

The proposed “identically zero” GHSL vertical term is false at polygon aggregate level. None of
11,422 UCDB polygons has an exactly constant `GH_BUV_TOT / GH_BUS_TOT` ratio across all 12
epochs; median relative span is 11.0%. This does not rescue a vertical-growth interpretation.
Each epoch's changing built-surface mask samples a different spatial subset of the same 2018
height field. The nonzero residual-height term is support composition, not observed height change.

## Gushiegu, Ghana pilot

Four exact public Cloud Storage tiles intersecting fixed 2025 UCDB polygon 3500 were acquired
for 2016 and 2023. At the middle 0.5 presence threshold, annualized modeled volume growth is
4.68%: +6.32% horizontal and −1.63% mean-height change. The corresponding shares are 135%
and −35%; shares can exceed 100% or be negative when components offset. Thresholds 0.3 and
0.7 preserve the same direction. This is one model-derived pilot, not a general city-growth
finding and not evidence of a causal development mechanism.

The registered result is `results/open_buildings_gushiegu_decomposition.csv`. No general
vertical-versus-horizontal claim is promoted to `research-status.md`.

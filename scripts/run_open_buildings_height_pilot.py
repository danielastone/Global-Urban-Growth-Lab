"""Aggregate Open Buildings Temporal tiles to one fixed UCDB polygon.

Requires the optional geospatial environment: geopandas, rasterio, and shapely.
Raw tiles and UCDB geometry remain outside Git and must be manifest-registered.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from urban_growth.built_form import built_form_decomposition


def aggregate_year(tile_paths, geometry, *, threshold: float) -> dict[str, float]:
    import rasterio
    from rasterio.mask import mask

    surface = volume = 0.0
    for path in tile_paths:
        with rasterio.open(path) as dataset:
            projected = geometry.to_crs(dataset.crs).geometry.iloc[0]
            values, transform = mask(dataset, [projected], crop=True, filled=False)
        height, presence = values[1], values[2]
        selected = (
            (~height.mask) & (~presence.mask) & (height.data > 0)
            & (presence.data >= threshold)
        )
        pixel_area = abs(transform.a * transform.e)
        surface += float(selected.sum() * pixel_area)
        volume += float((height.data[selected] * pixel_area).sum())
    if surface <= 0 or volume <= 0:
        raise ValueError("No positive selected building pixels inside the polygon")
    return {"surface": surface, "volume": volume}


def main() -> None:
    import geopandas as gpd

    parser = argparse.ArgumentParser()
    parser.add_argument("--ucdb-gpkg", type=Path, required=True)
    parser.add_argument("--city-id", type=int, required=True)
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    parser.add_argument("--start-tiles", nargs="+", type=Path, required=True)
    parser.add_argument("--end-tiles", nargs="+", type=Path, required=True)
    parser.add_argument("--thresholds", nargs="+", type=float, default=[0.3, 0.5, 0.7])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    polygons = gpd.read_file(
        args.ucdb_gpkg, layer="GHSL_UCDB_THEME_GHSL_GLOBE_R2024A"
    )
    polygon = polygons.loc[polygons["ID_UC_G0"].eq(args.city_id)]
    if len(polygon) != 1:
        raise ValueError("Expected exactly one fixed UCDB polygon")
    rows = []
    for threshold in args.thresholds:
        start = aggregate_year(args.start_tiles, polygon, threshold=threshold)
        end = aggregate_year(args.end_tiles, polygon, threshold=threshold)
        rows.append({
            "city_id": str(args.city_id), "period_start": args.start_year,
            "period_end": args.end_year, "presence_threshold": threshold,
            "built_up_surface_start_m2": start["surface"],
            "built_up_surface_end_m2": end["surface"],
            "built_up_volume_start_m3": start["volume"],
            "built_up_volume_end_m3": end["volume"],
            "height_lineage": "google_open_buildings_temporal_v1_independent_height",
        })
    result = built_form_decomposition(pd.DataFrame(rows))
    if not np.allclose(result["decomposition_identity_residual"], 0, atol=1e-12):
        raise RuntimeError("Decomposition identity failed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)


if __name__ == "__main__":
    main()

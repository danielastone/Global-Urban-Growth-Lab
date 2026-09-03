"""Origin-first overlap audit for Japan's official Population Census DIDs."""

from __future__ import annotations

from io import BytesIO
from itertools import pairwise
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd
import shapefile
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform
from shapely.strtree import STRtree

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

YEARS = (2000, 2005, 2010, 2015, 2020)
_TO_EQUAL_AREA = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)


def official_archive_names() -> list[str]:
    """Return the complete registered A16 archive universe for 2000--2020."""
    names = [f"A16-{year}_GML.zip" for year in ("10", "15", "20")]
    names.extend(
        f"A16-{year}_{pref:02d}_GML.zip"
        for year in ("00", "05")
        for pref in range(1, 48)
    )
    return sorted(names)


def official_archive_url(name: str) -> str:
    year = name.split("-")[1].split("_")[0]
    if name not in official_archive_names():
        raise SourceSchemaError(f"Unregistered Japan DID archive name: {name}")
    return f"https://nlftp.mlit.go.jp/ksj/gml/data/A16/A16-{year}/{name}"


def _archive_reader(path: Path) -> shapefile.Reader:
    with ZipFile(path) as archive:
        names = archive.namelist()
        shp_name = next((name for name in names if name.lower().endswith(".shp")), None)
        if shp_name is None:
            raise SourceSchemaError(f"Japan DID archive lacks a shapefile: {path.name}")
        stem = shp_name[:-4]
        required = {f"{stem}.shp", f"{stem}.shx", f"{stem}.dbf"}
        if not required.issubset(names):
            raise SourceSchemaError(f"Japan DID archive is incomplete: {path.name}")
        # Legacy A16 DBFs use Microsoft's Windows-31J extensions, not strict Shift-JIS.
        encoding = "utf-8" if any(name.lower().endswith(".cpg") for name in names) else "cp932"
        return shapefile.Reader(
            shp=BytesIO(archive.read(f"{stem}.shp")),
            shx=BytesIO(archive.read(f"{stem}.shx")),
            dbf=BytesIO(archive.read(f"{stem}.dbf")),
            encoding=encoding,
        )


def read_official_did_archives(raw_dir: Path) -> pd.DataFrame:
    """Read the registered MLIT A16 archives into a validated five-wave panel."""
    expected = official_archive_names()
    missing = [name for name in expected if not (raw_dir / name).is_file()]
    if missing:
        raise SourceSchemaError(f"Japan DID archives missing: {', '.join(missing[:5])}")
    rows: list[dict[str, object]] = []
    for name in expected:
        reader = _archive_reader(raw_dir / name)
        for position, shape_record in enumerate(reader.iterShapeRecords()):
            record = shape_record.record.as_dict()
            required = {"A16_002", "A16_003", "A16_004", "A16_005", "A16_006", "A16_011"}
            if not required.issubset(record):
                raise SourceSchemaError(f"Japan DID schema changed in {name}")
            # The nationwide files include zero-valued "affiliation undetermined"
            # placeholders that are not census DIDs and have no reference year.
            if (
                record["A16_011"] is None
                or int(record["A16_005"] or 0) <= 0
                or float(record["A16_006"] or 0) <= 0
            ):
                continue
            year = int(record["A16_011"])
            geometry = shape(shape_record.shape.__geo_interface__)
            if geometry.is_empty or not geometry.is_valid:
                geometry = geometry.buffer(0)
            if geometry.is_empty or not geometry.is_valid:
                raise SourceSchemaError(f"Japan DID has invalid geometry in {name}")
            rows.append(
                {
                    "year": year,
                    "source_archive": name,
                    "source_position": position,
                    "did_id_vintage": (
                        f"{str(record['A16_002']).zfill(5)}_"
                        f"{int(record['A16_004']):02d}"
                    ),
                    "municipality_code": str(record["A16_002"]).zfill(5),
                    "municipality_name": str(record["A16_003"]),
                    "population": int(record["A16_005"]),
                    "published_area_km2": float(record["A16_006"]),
                    "geometry": geometry,
                }
            )
    panel = pd.DataFrame(rows)
    if set(panel["year"].unique()) != set(YEARS):
        raise SourceSchemaError("Japan DID archives do not contain exactly the registered waves")
    reject_duplicate_keys(
        panel, ["year", "source_archive", "source_position"], source_name="Japan DID panel"
    )
    return panel.sort_values(["year", "source_archive", "source_position"]).reset_index(drop=True)


def _projected(geometry: object) -> object:
    return transform(_TO_EQUAL_AREA.transform, geometry)


def audit_adjacent_did_overlap(
    panel: pd.DataFrame,
    *,
    minimum_origin_population: int = 25_000,
    maximum_origin_population: int = 100_000,
    material_overlap: float = 0.01,
    identity_overlap: float = 0.50,
    stable_overlap: float = 0.995,
) -> pd.DataFrame:
    """Retain every origin-cohort DID and classify its next-wave overlap."""
    require_columns(
        panel,
        {"year", "population", "geometry", "did_id_vintage", "municipality_code"},
        source_name="Japan DID panel",
    )
    if not 0 < material_overlap < identity_overlap <= stable_overlap <= 1:
        raise SourceSchemaError("Japan DID overlap thresholds are invalid")
    if minimum_origin_population <= 0 or maximum_origin_population < minimum_origin_population:
        raise SourceSchemaError("Japan DID origin population bounds are invalid")
    results: list[dict[str, object]] = []
    for origin_year, endpoint_year in pairwise(YEARS):
        origin = panel.loc[panel["year"].eq(origin_year)].copy().reset_index(drop=True)
        endpoint = panel.loc[panel["year"].eq(endpoint_year)].copy().reset_index(drop=True)
        origin["projected_geometry"] = origin["geometry"].map(_projected)
        endpoint["projected_geometry"] = endpoint["geometry"].map(_projected)
        endpoint_geometries = endpoint["projected_geometry"].tolist()
        tree = STRtree(endpoint_geometries)
        candidate_map: dict[int, list[tuple[int, float, float, float]]] = {}
        endpoint_material_origins: dict[int, set[int]] = {}
        for origin_index, origin_geometry in enumerate(origin["projected_geometry"]):
            origin_area = float(origin_geometry.area)
            candidates: list[tuple[int, float, float, float]] = []
            for endpoint_index in tree.query(origin_geometry):
                endpoint_index = int(endpoint_index)
                endpoint_geometry = endpoint_geometries[endpoint_index]
                intersection = float(origin_geometry.intersection(endpoint_geometry).area)
                if intersection <= 0:
                    continue
                origin_ratio = intersection / origin_area
                endpoint_ratio = intersection / float(endpoint_geometry.area)
                candidates.append((endpoint_index, intersection, origin_ratio, endpoint_ratio))
                if max(origin_ratio, endpoint_ratio) >= material_overlap:
                    endpoint_material_origins.setdefault(endpoint_index, set()).add(origin_index)
            candidate_map[origin_index] = candidates

        cohort = origin["population"].between(
            minimum_origin_population, maximum_origin_population, inclusive="both"
        )
        for origin_index, origin_row in origin.loc[cohort].iterrows():
            candidates = candidate_map[int(origin_index)]
            material = [item for item in candidates if max(item[2], item[3]) >= material_overlap]
            best = max(candidates, key=lambda item: item[1]) if candidates else None
            row: dict[str, object] = {
                "origin_year": origin_year,
                "endpoint_year": endpoint_year,
                "origin_row_id": f"{origin_year}:{origin_row['source_archive']}:{origin_row['source_position']}",
                "origin_did_id_vintage": origin_row["did_id_vintage"],
                "origin_municipality_code": origin_row["municipality_code"],
                "origin_population": int(origin_row["population"]),
                "cohort_defined_at_origin": True,
                "cohort_uses_endpoint_population": False,
                "material_endpoint_count": len(material),
                "matched_endpoint_row_id": pd.NA,
                "matched_endpoint_did_id_vintage": pd.NA,
                "endpoint_population": np.nan,
                "origin_overlap_ratio": np.nan,
                "endpoint_overlap_ratio": np.nan,
                "endpoint_material_origin_count": 0,
                "dynamic_identity_resolved": False,
                "strict_stable_resolved": False,
                "concordance_status": "no_spatial_overlap",
            }
            if best is not None:
                endpoint_index, _, origin_ratio, endpoint_ratio = best
                endpoint_row = endpoint.iloc[endpoint_index]
                endpoint_origin_count = len(endpoint_material_origins.get(endpoint_index, set()))
                one_to_one = len(material) == 1 and endpoint_origin_count == 1
                row.update(
                    {
                        "matched_endpoint_row_id": (
                            f"{endpoint_year}:{endpoint_row['source_archive']}:"
                            f"{endpoint_row['source_position']}"
                        ),
                        "matched_endpoint_did_id_vintage": endpoint_row["did_id_vintage"],
                        "endpoint_population": int(endpoint_row["population"]),
                        "origin_overlap_ratio": origin_ratio,
                        "endpoint_overlap_ratio": endpoint_ratio,
                        "endpoint_material_origin_count": endpoint_origin_count,
                        "dynamic_identity_resolved": bool(
                            one_to_one and min(origin_ratio, endpoint_ratio) >= identity_overlap
                        ),
                        "strict_stable_resolved": bool(
                            one_to_one and min(origin_ratio, endpoint_ratio) >= stable_overlap
                        ),
                        "concordance_status": (
                            "one_to_one"
                            if one_to_one
                            else "split_or_merge_or_multiple_material_overlaps"
                        ),
                    }
                )
            results.append(row)
    result = pd.DataFrame(results)
    reject_duplicate_keys(result, ["origin_row_id"], source_name="Japan DID overlap audit")
    return result.sort_values(["origin_year", "origin_row_id"]).reset_index(drop=True)


def did_overlap_coverage(audit: pd.DataFrame) -> pd.DataFrame:
    """Report identity and strict-stability coverage against every origin denominator."""
    require_columns(
        audit,
        {"origin_year", "origin_population", "dynamic_identity_resolved", "strict_stable_resolved"},
        source_name="Japan DID overlap audit",
    )
    rows: list[dict[str, object]] = []
    for year, group in audit.groupby("origin_year"):
        total_population = float(group["origin_population"].sum())
        for rule in ["dynamic_identity_resolved", "strict_stable_resolved"]:
            resolved = group[rule].astype(bool)
            rows.append(
                {
                    "origin_year": int(year),
                    "concordance_rule": rule,
                    "origin_denominator_rows": len(group),
                    "resolved_rows": int(resolved.sum()),
                    "unresolved_rows": int((~resolved).sum()),
                    "count_coverage": float(resolved.mean()),
                    "origin_population_coverage": float(
                        group.loc[resolved, "origin_population"].sum() / total_population
                    ),
                    "denominator_defined_before_concordance": True,
                }
            )
    return pd.DataFrame(rows)


def build_did_direct_count_intervals(
    audit: pd.DataFrame, *, resolution_column: str = "dynamic_identity_resolved"
) -> pd.DataFrame:
    """Build three-wave direct-count rows only where both adjacent transitions resolve."""
    if resolution_column not in {"dynamic_identity_resolved", "strict_stable_resolved"}:
        raise SourceSchemaError("Unknown Japan DID concordance resolution rule")
    require_columns(
        audit,
        {
            "origin_year", "endpoint_year", "origin_row_id", "matched_endpoint_row_id",
            "origin_population", "endpoint_population", resolution_column,
        },
        source_name="Japan DID overlap audit",
    )
    rows: list[dict[str, object]] = []
    for forecast_origin in YEARS[1:-1]:
        prior = audit.loc[
            audit["endpoint_year"].eq(forecast_origin) & audit[resolution_column]
        ].copy()
        future = audit.loc[
            audit["origin_year"].eq(forecast_origin) & audit[resolution_column]
        ].copy()
        joined = prior.merge(
            future,
            left_on="matched_endpoint_row_id",
            right_on="origin_row_id",
            how="inner",
            suffixes=("_prior", "_future"),
            validate="one_to_one",
        )
        for _, row in joined.iterrows():
            lag = float(row["origin_population_prior"])
            origin = float(row["endpoint_population_prior"])
            endpoint = float(row["endpoint_population_future"])
            rows.append(
                {
                    "country_code": "JPN",
                    "locality_id": row["origin_row_id_future"],
                    "period_start": forecast_origin,
                    "period_end": forecast_origin + 5,
                    "population_lag": lag,
                    "population_start": origin,
                    "population_end": endpoint,
                    "recent_growth": float((np.log(origin) - np.log(lag)) / 5),
                    "future_growth": float((np.log(endpoint) - np.log(origin)) / 5),
                    "concordance_rule": resolution_column,
                    "source": "direct_count",
                    "analysis_eligible": True,
                    "concordance_quality": resolution_column,
                    "census_recency_years": 0,
                    "boundary_mode": "dynamic_did",
                }
            )
    return pd.DataFrame(rows)


def direct_count_persistence_diagnostics(intervals: pd.DataFrame) -> pd.DataFrame:
    """Describe Japan direct-count persistence without claiming a GHSL comparison."""
    require_columns(
        intervals,
        {"period_start", "recent_growth", "future_growth", "concordance_rule"},
        source_name="Japan DID direct-count intervals",
    )
    rows: list[dict[str, object]] = []
    for (rule, origin), group in intervals.groupby(["concordance_rule", "period_start"]):
        x = group["recent_growth"].to_numpy(dtype=float)
        y = group["future_growth"].to_numpy(dtype=float)
        intercept, beta = np.linalg.lstsq(
            np.column_stack([np.ones(len(x)), x]), y, rcond=None
        )[0]
        error = y - x
        rows.append(
            {
                "concordance_rule": rule,
                "period_start": int(origin),
                "n": len(group),
                "persistence_intercept": float(intercept),
                "persistence_beta": float(beta),
                "persistence_mae": float(np.mean(np.abs(error))),
                "persistence_rmse": float(np.sqrt(np.mean(error**2))),
                "sign_reversal_rate": float(np.mean(np.sign(x) != np.sign(y))),
                "mean_growth_curvature": float(np.mean(y - x)),
                "mean_absolute_growth_curvature": float(np.mean(np.abs(y - x))),
            }
        )
    return pd.DataFrame(rows)

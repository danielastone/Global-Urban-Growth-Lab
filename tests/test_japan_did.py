import pandas as pd
from shapely.geometry import box

from urban_growth.japan_did import (
    audit_adjacent_did_overlap,
    build_did_direct_count_intervals,
    did_overlap_coverage,
    official_archive_names,
    official_archive_url,
)


def _row(year: int, row_id: str, population: int, geometry: object) -> dict[str, object]:
    return {
        "year": year,
        "source_archive": f"{year}.zip",
        "source_position": row_id,
        "did_id_vintage": row_id,
        "municipality_code": "00001",
        "population": population,
        "geometry": geometry,
    }


def test_official_archive_universe_is_complete() -> None:
    names = official_archive_names()
    assert len(names) == 97
    assert len(set(names)) == 97
    assert official_archive_url("A16-20_GML.zip").endswith("/A16-20/A16-20_GML.zip")


def test_overlap_audit_preserves_origin_denominator_and_marks_split() -> None:
    rows = []
    for year in (2000, 2005, 2010, 2015, 2020):
        rows.append(_row(year, "stable", 50_000, box(130, 30, 131, 31)))
    rows.extend(
        [
            _row(2000, "split", 60_000, box(132, 30, 134, 31)),
            _row(2005, "split-a", 30_000, box(132, 30, 133, 31)),
            _row(2005, "split-b", 30_000, box(133, 30, 134, 31)),
        ]
    )
    audit = audit_adjacent_did_overlap(pd.DataFrame(rows))
    first = audit.loc[audit["origin_year"].eq(2000)]
    assert len(first) == 2
    split = first.loc[first["origin_did_id_vintage"].eq("split")].iloc[0]
    assert split["material_endpoint_count"] == 2
    assert not split["dynamic_identity_resolved"]
    coverage = did_overlap_coverage(audit)
    dynamic = coverage.loc[
        coverage["origin_year"].eq(2000)
        & coverage["concordance_rule"].eq("dynamic_identity_resolved")
    ].iloc[0]
    assert dynamic["origin_denominator_rows"] == 2
    assert dynamic["resolved_rows"] == 1


def test_intervals_require_both_adjacent_transitions() -> None:
    rows = [
        _row(year, "stable", population, box(130, 30, 131, 31))
        for year, population in zip(
            (2000, 2005, 2010, 2015, 2020),
            (40_000, 45_000, 50_000, 55_000, 60_000),
            strict=True,
        )
    ]
    audit = audit_adjacent_did_overlap(pd.DataFrame(rows))
    intervals = build_did_direct_count_intervals(audit)
    assert intervals["period_start"].tolist() == [2005, 2010, 2015]
    assert intervals["population_start"].tolist() == [45_000.0, 50_000.0, 55_000.0]
    assert intervals["analysis_eligible"].all()

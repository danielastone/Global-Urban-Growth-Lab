from pathlib import Path

import pandas as pd

from urban_growth.wup_source_basis import (
    attach_wup_source_basis,
    evaluate_wup_h1_by_source_basis,
    read_wup_m01_source_metadata,
    source_basis_classification_rows,
)


def _intervals() -> pd.DataFrame:
    rows = []
    for origin in [1990, 1995, 2000]:
        for city_id, country, recent in [
            (1, "A", 0.01),
            (2, "A", 0.03),
            (3, "B", 0.02),
            (4, "B", 0.04),
            (5, "C", 0.025),
        ]:
            rows.append(
                {
                    "city_id": city_id,
                    "country_code": country,
                    "period_start": origin,
                    "period_end": origin + 5,
                    "population_start": 100_000 + city_id * 10_000,
                    "recent_growth": recent,
                    "future_growth": 0.5 * recent + (0.002 if country == "A" else 0.004),
                }
            )
    return pd.DataFrame(rows)


def _metadata() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "country_code": ["A", "B"],
            "source_process_type": ["Census", "Estimate"],
            "source_population_year": pd.Series([1990, 1988], dtype="Int64"),
            "source_admin_level": pd.Series([2, 3], dtype="Int64"),
        }
    )


def test_attach_source_basis_preserves_country_proxy_limit() -> None:
    result = attach_wup_source_basis(_intervals(), _metadata())
    test = result.loc[result["period_start"].eq(2000)].set_index("country_code")
    assert test.loc["A", "source_recency_stratum"].iloc[0] == "recent_direct_input"
    assert test.loc["B", "source_recency_stratum"].iloc[0] == "estimate_input"
    assert test.loc["C", "source_recency_stratum"] == "unresolved"
    assert result["city_direct_observation_status"].eq("unresolved").all()
    assert (
        result.loc[result["country_code"].eq("A"), "city_source_resolution"]
        .eq("country_proxy_only")
        .all()
    )


def test_source_basis_rows_are_explicit_and_unique() -> None:
    classified = attach_wup_source_basis(_intervals(), _metadata())
    rows = source_basis_classification_rows(classified)
    assert len(rows) == len(classified)
    assert not rows.duplicated(["city_id", "period_start", "period_end"]).any()
    assert rows["city_direct_observation_status"].notna().all()


def test_source_basis_h1_reports_strata_and_country_balancing() -> None:
    classified = attach_wup_source_basis(_intervals(), _metadata())
    result = evaluate_wup_h1_by_source_basis(classified, [2000])
    assert set(result["weighting"]) == {"row_weighted", "country_balanced"}
    assert set(result["stratification"]) == {
        "recency",
        "process_type",
        "admin_level",
    }
    assert result["test_rows_identical"].all()
    assert result["training_precedes_origin"].all()
    assert result["city_direct_observation_status"].eq("unresolved").all()
    assert result["population_coverage_fraction"].between(0, 1).all()


def test_read_m01_normalizes_registered_fields(tmp_path: Path) -> None:
    path = tmp_path / "m01.xlsx"
    frame = pd.DataFrame(
        {
            "ISO3_Code": ["AAA"],
            "Location": ["Alpha"],
            "DataProcessType": ["Census"],
            "DataProcess": ["Population and Housing Census"],
            "DataStatusName": ["Final"],
            "Input_Pop_year": [2010],
            "Input_Pop_level": [2],
            "Input_Pop_source": ["Official census"],
        }
    )
    frame.to_excel(path, sheet_name="Input_Metadata", index=False)
    result = read_wup_m01_source_metadata(str(path))
    assert result.loc[0, "country_code"] == "AAA"
    assert result.loc[0, "source_population_year"] == 2010

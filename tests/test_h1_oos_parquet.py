import numpy as np
import pandas as pd

from urban_growth.h1_oos import (
    attach_strict_country_peer_growth,
    build_five_year_intervals,
    fit_rolling_oos,
)


def _synthetic_panel() -> pd.DataFrame:
    rows = []
    years = [2000, 2005, 2010, 2015, 2020]
    for country_index in range(31):
        country = f"C{country_index:02d}"
        for city_index in range(4):
            city_id = f"{country}-{city_index}"
            rate = 0.006 + country_index * 0.00008 + city_index * 0.0007
            base = 60_000 + country_index * 1_000 + city_index * 500
            for year in years:
                rows.append(
                    {
                        "city_id": city_id,
                        "ISO3_Code": country,
                        "City_Name": city_id,
                        "year": year,
                        "population": base * np.exp(rate * (year - 2000)),
                        "observation_type": "estimate",
                    }
                )
    return pd.DataFrame(rows)


def test_h1_oos_scoring_panel_roundtrips_parquet_with_lineage(tmp_path):
    intervals = build_five_year_intervals(_synthetic_panel())
    strict, _ = attach_strict_country_peer_growth(intervals)
    panel, _ = fit_rolling_oos(strict, construction_commit="deadbeef")

    path = tmp_path / "h1_oos_rows.parquet"
    panel.to_parquet(path, index=False)
    restored = pd.read_parquet(path)

    assert len(restored) == len(panel)
    assert {
        "wup_vintage",
        "period_start",
        "period_end",
        "horizon_years",
        "growth_window_years",
        "construction_commit",
        "panel_spec_version",
        "b0_prediction",
        "b1_prediction",
        "b0_error",
        "b1_error",
    }.issubset(restored.columns)
    assert restored["construction_commit"].eq("deadbeef").all()

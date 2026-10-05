from pathlib import Path

import numpy as np
import pandas as pd

from urban_growth.h1_oos import attach_strict_country_peer_growth, build_five_year_intervals
from urban_growth.h1_panel_freeze import (
    FORBIDDEN_PR_A_COLUMNS,
    PANEL_HASH_METHOD,
    canonical_panel_sha256,
    freeze_scoring_panel,
    panel_diagnostics,
)


def _synthetic_city_year_panel(
    *,
    country_count: int = 31,
    cities_per_country: int = 4,
) -> pd.DataFrame:
    rows = []
    years = [2000, 2005, 2010, 2015, 2020]
    for country_index in range(country_count):
        country = f"C{country_index:02d}"
        for city_index in range(cities_per_country):
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


def _frozen_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    intervals = build_five_year_intervals(_synthetic_city_year_panel())
    strict, _ = attach_strict_country_peer_growth(intervals)
    return freeze_scoring_panel(strict, construction_commit="deadbeef")


def test_freeze_panel_uses_same_eligible_origins_without_model_outputs():
    panel, eligibility = _frozen_panel()
    assert eligibility.loc[eligibility["eligible"], "origin"].tolist() == [2010, 2015]
    assert not FORBIDDEN_PR_A_COLUMNS.intersection(panel.columns)
    assert panel["training_precedes_or_equals_origin"].all()
    assert panel["b0_b1_training_rows_identical"].all()
    assert panel["b0_b1_scoring_rows_identical"].all()


def test_panel_diagnostics_are_outcome_blind_and_weights_sum_to_one():
    panel, eligibility = _frozen_panel()
    diagnostics = panel_diagnostics(panel, eligibility)
    assert diagnostics["eligible_origins"] == [2010, 2015]
    assert diagnostics["schema_checks"]["required_lineage_columns_present"] is True
    assert diagnostics["schema_checks"]["forbidden_performance_columns_present"] == []
    assert diagnostics["schema_checks"]["duplicate_city_origin_rows"] == 0
    assert diagnostics["leakage_assertions"] == {
        "all_training_precedes_or_equals_origin": True,
        "all_country_peer_leave_city_out": True,
        "no_country_peer_future_use": True,
    }
    for row in diagnostics["origin_diagnostics"]:
        assert np.isclose(row["country_balanced_weight_sum"], 1.0)
        assert np.isclose(row["row_weighted_weight_sum"], 1.0)
        assert row["paired_training_rows"] is True
        assert row["paired_scoring_rows"] is True
        assert row["training_max_period_end"] <= row["origin"]
        prohibited_keys = {
            "rmse",
            "mae",
            "relative_rmse_improvement",
            "mae_difference",
            "gate_passed",
            "winner",
        }
        assert not prohibited_keys.intersection(row)


def test_canonical_panel_hash_is_order_invariant_and_content_sensitive():
    panel, _ = _frozen_panel()
    baseline = canonical_panel_sha256(panel)
    shuffled = panel.sample(frac=1.0, random_state=17).reset_index(drop=True)
    assert PANEL_HASH_METHOD == "canonical-jsonl-v1"
    assert canonical_panel_sha256(shuffled) == baseline

    changed = panel.copy()
    changed.loc[0, "population_origin"] = float(changed.loc[0, "population_origin"]) + 1.0
    assert canonical_panel_sha256(changed) != baseline


def test_pr_a_module_source_contains_no_performance_builder_call():
    source = (
        Path(__file__).parents[1]
        / "src"
        / "urban_growth"
        / "h1_panel_freeze.py"
    ).read_text(encoding="utf-8")
    assert "fit_rolling_oos(" not in source
    assert "summarize_oos(" not in source
    assert "_result_payload(" not in source
    assert "h1_oos_summary.csv" not in source
    assert "RESULT-H1-OOS" not in source

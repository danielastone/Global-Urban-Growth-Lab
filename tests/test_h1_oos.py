from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from urban_growth.h1_oos import (
    COMPLETE_RESULT_ID,
    INCONCLUSIVE_RESULT_ID,
    PROTOCOL,
    attach_strict_country_peer_growth,
    build_five_year_intervals,
    derive_eligible_origins,
    fit_rolling_oos,
    summarize_oos,
)
from urban_growth.knowledge_graph.lifecycle import evaluate_gate
from urban_growth.knowledge_graph.models import parse_node


def _synthetic_city_year_panel(
    *,
    country_count: int = 31,
    cities_per_country: int = 4,
    add_singleton: bool = False,
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
    if add_singleton:
        for year in years:
            rows.append(
                {
                    "city_id": "SINGLE-0",
                    "ISO3_Code": "SNG",
                    "City_Name": "Singleton",
                    "year": year,
                    "population": 75_000 * np.exp(0.01 * (year - 2000)),
                    "observation_type": "estimate",
                }
            )
    return pd.DataFrame(rows)


def test_strict_country_peer_excludes_singletons_without_global_fallback():
    intervals = build_five_year_intervals(_synthetic_city_year_panel(add_singleton=True))
    strict, exclusions = attach_strict_country_peer_growth(intervals)
    assert "SNG" not in set(strict["country_code"])
    assert set(exclusions["country_code"]) == {"SNG"}
    assert exclusions["excluded_city_rows"].sum() == intervals["period_start"].nunique()
    assert not strict["country_peer_recent_growth_loo"].isna().any()


def test_origin_eligibility_requires_both_100_rows_and_30_countries():
    enough = build_five_year_intervals(_synthetic_city_year_panel())
    enough, _ = attach_strict_country_peer_growth(enough)
    eligibility = derive_eligible_origins(enough)
    assert eligibility.loc[eligibility["eligible"], "origin"].tolist() == [2010, 2015]

    too_few_countries = build_five_year_intervals(
        _synthetic_city_year_panel(country_count=29, cities_per_country=4)
    )
    too_few_countries, _ = attach_strict_country_peer_growth(too_few_countries)
    assert not derive_eligible_origins(too_few_countries)["eligible"].any()

    too_few_rows = build_five_year_intervals(
        _synthetic_city_year_panel(country_count=31, cities_per_country=3)
    )
    too_few_rows, _ = attach_strict_country_peer_growth(too_few_rows)
    too_few_rows = too_few_rows.loc[too_few_rows["period_start"] <= 2010]
    assert not derive_eligible_origins(too_few_rows)["eligible"].any()


def test_rolling_oos_enforces_no_future_training_and_paired_rows():
    intervals = build_five_year_intervals(_synthetic_city_year_panel())
    strict, _ = attach_strict_country_peer_growth(intervals)
    panel, eligibility = fit_rolling_oos(strict, construction_commit="deadbeef")
    assert eligibility.loc[eligibility["eligible"], "origin"].tolist() == [2010, 2015]
    assert panel["training_precedes_or_equals_origin"].all()
    assert (panel["training_max_period_end"] <= panel["period_start"]).all()
    assert panel["b0_b1_training_rows_identical"].all()
    assert panel["b0_b1_scoring_rows_identical"].all()
    assert panel[["b0_prediction", "b1_prediction", "b0_error", "b1_error"]].notna().all().all()


def test_summary_has_locked_gate_fields_equal_origin_aggregation_and_no_winner():
    intervals = build_five_year_intervals(_synthetic_city_year_panel())
    strict, _ = attach_strict_country_peer_growth(intervals)
    panel, _ = fit_rolling_oos(strict, construction_commit="deadbeef")
    summary = summarize_oos(panel)
    assert set(summary["weighting"]) == {"country_balanced", "row_weighted"}
    assert set(summary["scope"]) == {"origin", "aggregate"}
    assert summary.loc[summary["scope"].eq("aggregate")].shape[0] == 2
    assert {
        "rmse_condition_passed",
        "mae_condition_passed",
        "gate_passed",
        "relative_rmse_improvement",
        "mae_difference",
    }.issubset(summary.columns)
    assert "winner" not in summary.columns


def test_w2_probe_missing_mae_is_inconclusive_under_production_gate():
    gate = parse_node(
        {
            "id": "GATE-H1-PERSISTENCE-OOS",
            "type": "acceptance_gate",
            "title": "H1 predictive improvement gate",
            "canonical_name": "H1 OOS predictive gate",
            "aliases": [],
            "conditions": [
                {"metric": "relative_rmse_improvement", "operator": ">=", "threshold": 0.05},
                {"metric": "mae_difference", "operator": "<=", "threshold": 0.0},
            ],
            "failure_interpretation": "falsifies_primary_claim",
            "relations": [],
        }
    )
    result = parse_node(
        {
            "id": INCONCLUSIVE_RESULT_ID,
            "type": "result",
            "title": "probe",
            "canonical_name": "probe",
            "aliases": [],
            "test": "TEST-H1-PERSISTENCE-OOS",
            "status": "completed",
            "executed_at": "2026-09-07T00:00:00+00:00",
            "metrics": {"relative_rmse_improvement": 0.06},
            "execution": {"commit": "deadbeef"},
            "sample": {},
            "inputs": {},
            "relations": [],
        }
    )
    assert evaluate_gate(result, gate).outcome == "inconclusive"


def test_protocol_manifest_reserves_both_result_ids():
    path = Path(__file__).parents[1] / "knowledge" / "schema" / "h1-oos-wup-v1.yaml"
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert spec["primary_test"]["horizon_years"] == PROTOCOL.horizon_years == 5
    assert spec["origin_eligibility"]["minimum_training_rows"] == 100
    assert spec["origin_eligibility"]["minimum_training_countries"] == 30
    assert spec["w2"]["reserved_result_ids"] == {
        "inconclusive_probe": INCONCLUSIVE_RESULT_ID,
        "completed": COMPLETE_RESULT_ID,
    }

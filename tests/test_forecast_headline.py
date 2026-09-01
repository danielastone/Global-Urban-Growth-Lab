# ruff: noqa: I001

import pandas as pd
import pytest

from urban_growth.forecast_headline import (
    evaluate_headline_point_in_time_persistence,
    headline_point_in_time_persistence_errors,
)
from urban_growth.io import SourceSchemaError


POLICY_KWARGS = {
    "minimum_observed_outcome_share": 0.60,
    "coverage_policy_reference": "locked-test-coverage-policy",
}


def _panel() -> pd.DataFrame:
    rows = []
    specs = {
        "A": [(2000, 2005, 0.010, 0.012), (2005, 2010, 0.012, 0.014), (2010, 2015, 0.014, 0.013)],
        "B": [(2000, 2005, 0.020, 0.018), (2005, 2010, 0.018, 0.016), (2010, 2015, 0.016, 0.015)],
        "C": [(2000, 2005, -0.005, -0.004), (2005, 2010, -0.004, -0.002), (2010, 2015, -0.002, 0.001)],
    }
    for city_id, intervals in specs.items():
        for start, end, recent, future in intervals:
            rows.append(
                {
                    "city_id": city_id,
                    "country_code": "AAA" if city_id != "C" else "BBB",
                    "period_start": start,
                    "period_end": end,
                    "population_start": 50_000,
                    "recent_growth": recent,
                    "future_growth": future,
                    "growth_eligible": True,
                    "point_in_time_available": True,
                    "availability_provenance_verified": True,
                    "forecast_origin_date": f"{start}-12-31",
                    "outcome_available_date": f"{end}-06-30",
                    "outcome_available_reference": f"official-release-{end}",
                }
            )
    return pd.DataFrame(rows)


def _coverage() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "origin": [2005, 2010],
            "origin_risk_set_rows": [4, 5],
            "observed_outcome_rows": [3, 3],
            "missing_outcome_rows": [1, 2],
            "observed_outcome_share": [0.75, 0.60],
            "coverage_denominator_rule": [
                "lag_and_origin_predictors_only",
                "lag_and_origin_predictors_only",
            ],
            "future_outcome_used_for_membership": [False, False],
        }
    )


def test_headline_metrics_attach_origin_risk_set_coverage() -> None:
    result = evaluate_headline_point_in_time_persistence(
        _panel(), [2005, 2010], _coverage(), **POLICY_KWARGS
    )
    assert result["origin_risk_set_coverage_enforced"].all()
    assert result["headline_coverage_contract_enforced"].all()
    assert result["headline_coverage_minimum_enforced"].all()
    assert result["coverage_policy_passed"].all()
    assert result["minimum_observed_outcome_share"].eq(0.60).all()
    assert result["coverage_policy_reference"].eq("locked-test-coverage-policy").all()
    assert result["benchmark_stage"].eq("point_in_time_persistence_with_origin_coverage").all()
    assert result.loc[result["origin"].eq(2005), "origin_risk_set_rows"].eq(4).all()
    assert result.loc[result["origin"].eq(2010), "observed_outcome_share"].eq(0.60).all()


def test_headline_errors_attach_same_coverage_denominator() -> None:
    result = headline_point_in_time_persistence_errors(
        _panel(), [2005, 2010], _coverage(), **POLICY_KWARGS
    )
    assert result["origin_risk_set_coverage_enforced"].all()
    assert result["headline_coverage_contract_enforced"].all()
    assert result["headline_coverage_minimum_enforced"].all()
    assert result["coverage_policy_passed"].all()
    assert result.loc[result["origin"].eq(2010), "origin_risk_set_rows"].eq(5).all()


def test_headline_evaluation_requires_coverage_for_every_origin() -> None:
    coverage = _coverage().loc[_coverage()["origin"].eq(2005)].copy()
    with pytest.raises(SourceSchemaError, match="missing declared origins"):
        evaluate_headline_point_in_time_persistence(
            _panel(), [2005, 2010], coverage, **POLICY_KWARGS
        )


def test_headline_evaluation_rejects_future_defined_membership() -> None:
    coverage = _coverage()
    coverage.loc[coverage["origin"].eq(2010), "future_outcome_used_for_membership"] = True
    with pytest.raises(SourceSchemaError, match="Future outcome observability"):
        evaluate_headline_point_in_time_persistence(
            _panel(), [2005, 2010], coverage, **POLICY_KWARGS
        )


def test_headline_evaluation_rejects_inconsistent_coverage_counts() -> None:
    coverage = _coverage()
    coverage.loc[coverage["origin"].eq(2010), "missing_outcome_rows"] = 1
    with pytest.raises(SourceSchemaError, match="must equal the origin risk set"):
        evaluate_headline_point_in_time_persistence(
            _panel(), [2005, 2010], coverage, **POLICY_KWARGS
        )


def test_headline_evaluation_rejects_scored_rows_above_observed_outcomes() -> None:
    coverage = _coverage()
    coverage.loc[coverage["origin"].eq(2010), "observed_outcome_rows"] = 2
    coverage.loc[coverage["origin"].eq(2010), "missing_outcome_rows"] = 3
    coverage.loc[coverage["origin"].eq(2010), "observed_outcome_share"] = 0.4
    with pytest.raises(SourceSchemaError, match="below the registered headline minimum"):
        evaluate_headline_point_in_time_persistence(
            _panel(), [2005, 2010], coverage, **POLICY_KWARGS
        )


def test_headline_evaluation_fails_when_registered_minimum_is_not_met() -> None:
    with pytest.raises(SourceSchemaError, match="below the registered headline minimum"):
        evaluate_headline_point_in_time_persistence(
            _panel(),
            [2005, 2010],
            _coverage(),
            minimum_observed_outcome_share=0.70,
            coverage_policy_reference="locked-test-coverage-policy",
        )


def test_headline_evaluation_rejects_invalid_registered_minimum() -> None:
    with pytest.raises(SourceSchemaError, match=r"must be in \(0, 1\]"):
        evaluate_headline_point_in_time_persistence(
            _panel(),
            [2005, 2010],
            _coverage(),
            minimum_observed_outcome_share=0,
            coverage_policy_reference="locked-test-coverage-policy",
        )


def test_headline_evaluation_requires_coverage_policy_reference() -> None:
    with pytest.raises(SourceSchemaError, match="coverage_policy_reference"):
        evaluate_headline_point_in_time_persistence(
            _panel(),
            [2005, 2010],
            _coverage(),
            minimum_observed_outcome_share=0.60,
            coverage_policy_reference="  ",
        )

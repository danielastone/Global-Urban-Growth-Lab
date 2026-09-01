import pandas as pd

from urban_growth.forecast_coverage import (
    observed_outcome_scoring_keys,
    origin_risk_set_outcome_coverage,
)


def _panel() -> pd.DataFrame:
    rows = []
    for city_id, populations in {
        "A": {1995: 40_000, 2000: 50_000, 2005: 60_000},
        "B": {1995: 30_000, 2000: 45_000},
        "C": {1995: 20_000, 2000: 25_000, 2005: 27_000},
    }.items():
        for year, population in populations.items():
            rows.append(
                {
                    "city_id": city_id,
                    "year": year,
                    "population": population,
                    "observation_type": "estimate",
                }
            )
    frame = pd.DataFrame(rows)
    frame.loc[
        (frame["city_id"] == "C") & frame["year"].eq(2005),
        "observation_type",
    ] = "projection"
    return frame


def test_future_missing_city_remains_in_origin_risk_set_denominator() -> None:
    rows, summary = origin_risk_set_outcome_coverage(_panel(), [2000])
    assert set(rows["city_id"]) == {"A", "B", "C"}
    b = rows.loc[rows["city_id"].eq("B")].iloc[0]
    assert not bool(b["outcome_observed"])
    assert b["outcome_coverage_exclusion_reason"] == "missing_future_outcome_value"
    assert summary.loc[0, "origin_risk_set_rows"] == 3
    assert summary.loc[0, "observed_outcome_rows"] == 1
    assert summary.loc[0, "missing_outcome_rows"] == 2
    assert not bool(summary.loc[0, "future_outcome_used_for_membership"])


def test_disallowed_future_type_stays_in_denominator_but_not_scoring_keys() -> None:
    rows, _ = origin_risk_set_outcome_coverage(_panel(), [2000])
    c = rows.loc[rows["city_id"].eq("C")].iloc[0]
    assert bool(c["outcome_values_present"])
    assert not bool(c["outcome_types_allowed"])
    assert c["outcome_coverage_exclusion_reason"] == "future_outcome_type_not_allowed"
    scoring = observed_outcome_scoring_keys(rows)
    assert scoring.to_dict("records") == [{"city_id": "A", "origin": 2000}]


def test_future_population_change_cannot_change_origin_risk_set_membership() -> None:
    original_rows, _ = origin_risk_set_outcome_coverage(_panel(), [2000])
    changed = _panel()
    changed.loc[(changed["city_id"] == "A") & changed["year"].eq(2005), "population"] = 1
    changed_rows, _ = origin_risk_set_outcome_coverage(changed, [2000])
    assert original_rows[["city_id", "origin_risk_set_member"]].equals(
        changed_rows[["city_id", "origin_risk_set_member"]]
    )

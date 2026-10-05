from urban_growth.india_census_124 import (
    india_issue_124_source_register,
    qualify_india_issue_124_sources,
)


def test_a04_future_conditioned_history_is_not_validation() -> None:
    qualified, status = qualify_india_issue_124_sources(india_issue_124_source_register())
    a04 = qualified.set_index("candidate_id").loc["india_a04_2011_historical_town_series"]
    assert a04["exclusion_reason"] == "future_conditioned_town_universe"
    assert not a04["issue_124_qualified"]
    assert not status.iloc[0]["benchmark_estimable"]


def test_2001_2011_transition_is_allowed_but_cannot_close_issue() -> None:
    qualified, status = qualify_india_issue_124_sources(india_issue_124_source_register())
    pca = qualified.set_index("candidate_id").loc["india_pca_lcd_2001_2011"]
    assert pca["exclusion_reason"] == "insufficient_forecast_origins"
    assert status.iloc[0]["historical_2001_2011_transition_permitted"]
    assert not status.iloc[0]["historical_transition_closes_issue_124"]


def test_candidate_passes_only_after_all_identification_requirements() -> None:
    candidate = india_issue_124_source_register().iloc[[2]].copy()
    candidate["official_adjacent_wave_concordance"] = True
    candidate["usable_forecast_origins"] = 2
    candidate["release_status"] = "released"
    qualified, status = qualify_india_issue_124_sources(candidate)
    assert qualified.iloc[0]["issue_124_qualified"]
    assert status.iloc[0]["benchmark_estimable"]


def test_future_conditioning_overrides_nominal_wave_count() -> None:
    candidate = india_issue_124_source_register().iloc[[0]].copy()
    candidate["origin_denominator_available"] = True
    candidate["official_adjacent_wave_concordance"] = True
    candidate["usable_forecast_origins"] = 2
    qualified, _ = qualify_india_issue_124_sources(candidate)
    assert qualified.iloc[0]["exclusion_reason"] == "future_conditioned_town_universe"
    assert not qualified.iloc[0]["issue_124_qualified"]

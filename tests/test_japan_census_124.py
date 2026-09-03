from urban_growth.japan_census_124 import (
    japan_issue_124_source_register,
    qualify_japan_issue_124_sources,
)


def test_did_path_is_acquisition_ready_but_not_yet_empirically_qualified() -> None:
    qualified, status = qualify_japan_issue_124_sources(japan_issue_124_source_register())
    did = qualified.set_index("candidate_id").loc["japan_did_2000_2020"]
    assert did["acquisition_ready"]
    assert did["status"] == "acquisition_ready_inputs_not_registered"
    assert not did["issue_124_qualified"]
    assert status.iloc[0]["acquisition_ready_sources"] == 1
    assert not status.iloc[0]["benchmark_estimable"]


def test_municipality_panel_remains_administrative_sensitivity() -> None:
    qualified, _ = qualify_japan_issue_124_sources(japan_issue_124_source_register())
    municipality = qualified.set_index("candidate_id").loc[
        "japan_municipal_census_2000_2025"
    ]
    assert municipality["status"] == "not_comparable_locality_source"
    assert not municipality["acquisition_ready"]


def test_later_boundary_readjustment_cannot_define_earlier_origin_cohort() -> None:
    qualified, _ = qualify_japan_issue_124_sources(japan_issue_124_source_register())
    adjusted = qualified.set_index("candidate_id").loc[
        "japan_current_boundary_readjusted_municipal_history"
    ]
    assert adjusted["status"] == "future_conditioned_universe"
    assert not adjusted["issue_124_qualified"]


def test_did_path_qualifies_only_after_denominator_and_overlap_audit() -> None:
    candidate = japan_issue_124_source_register().iloc[[0]].copy()
    candidate["data_acquired"] = True
    candidate["origin_denominator_constructed"] = True
    partly, _ = qualify_japan_issue_124_sources(candidate)
    assert partly.iloc[0]["status"] == "geometry_overlap_not_audited"
    candidate["geometry_overlap_audited"] = True
    complete, status = qualify_japan_issue_124_sources(candidate)
    assert complete.iloc[0]["issue_124_qualified"]
    assert status.iloc[0]["benchmark_estimable"]

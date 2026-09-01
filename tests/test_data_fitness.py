import pandas as pd

from urban_growth.data_fitness import evaluate_city_data_fitness, headline_sample


def stable_row(**overrides):
    row = {
        "city_id": "example:1",
        "source_id": "source-a",
        "population_concept": "locality",
        "geographic_unit": "locality",
        "validation_status": "passed",
        "concordance_status": "stable",
        "boundary_change_status": "none",
        "boundary_temporally_fixed": True,
        "geographic_comparable": True,
        "temporal_comparable": True,
        "administrative_reclassification": False,
        "methodology_change": False,
        "known_inconsistency": False,
        "truncation_exposure": "none",
        "survivorship_exposure": "none",
        "coordinates_validated": True,
        "network_geography_validated": True,
        "raw_value": 52_000,
    }
    row.update(overrides)
    return row


def test_stable_validated_row_is_eligible_for_all_uses():
    result = evaluate_city_data_fitness(pd.DataFrame([stable_row()])).iloc[0]

    assert bool(result["level_eligible"])
    assert bool(result["growth_eligible"])
    assert bool(result["spatial_eligible"])
    assert bool(result["headline_eligible"])
    assert result["fitness_reasons"] == ""


def test_changing_boundary_blocks_growth_and_headline_but_not_valid_level_record():
    result = evaluate_city_data_fitness(
        pd.DataFrame(
            [
                stable_row(
                    boundary_temporally_fixed=False,
                    boundary_change_status="annexation",
                    concordance_status="uncertain",
                )
            ]
        )
    ).iloc[0]

    assert bool(result["level_eligible"])
    assert not bool(result["growth_eligible"])
    assert not bool(result["headline_eligible"])
    assert "unresolved_boundary_change" in result["growth_exclusion_reasons"]


def test_harmonized_common_geography_can_restore_growth_eligibility():
    result = evaluate_city_data_fitness(
        pd.DataFrame(
            [
                stable_row(
                    boundary_temporally_fixed=False,
                    boundary_change_status="annexation",
                    concordance_status="harmonized_common_geography",
                )
            ]
        )
    ).iloc[0]

    assert bool(result["growth_eligible"])
    assert bool(result["headline_eligible"])


def test_unknown_boundary_status_fails_growth_and_headline_closed():
    result = evaluate_city_data_fitness(
        pd.DataFrame([stable_row(boundary_change_status="partial")])
    ).iloc[0]

    assert bool(result["level_eligible"])
    assert not bool(result["growth_eligible"])
    assert not bool(result["headline_eligible"])
    assert "boundary_change_status_unknown" in result["growth_exclusion_reasons"]
    assert "boundary_change_status_unknown" in result["headline_exclusion_reasons"]


def test_missing_boundary_status_fails_growth_and_headline_closed():
    result = evaluate_city_data_fitness(
        pd.DataFrame([stable_row(boundary_change_status=None)])
    ).iloc[0]

    assert not bool(result["growth_eligible"])
    assert not bool(result["headline_eligible"])
    assert "boundary_change_status_unknown" in result["growth_exclusion_reasons"]


def test_harmonized_geography_can_resolve_unknown_boundary_status():
    result = evaluate_city_data_fitness(
        pd.DataFrame(
            [
                stable_row(
                    boundary_change_status="partial",
                    boundary_temporally_fixed=False,
                    concordance_status="harmonized_common_geography",
                )
            ]
        )
    ).iloc[0]

    assert bool(result["growth_eligible"])
    assert bool(result["headline_eligible"])


def test_geographic_comparability_is_required_for_growth_and_headline():
    result = evaluate_city_data_fitness(
        pd.DataFrame([stable_row(geographic_comparable=False)])
    ).iloc[0]

    assert not bool(result["level_eligible"])
    assert not bool(result["growth_eligible"])
    assert not bool(result["headline_eligible"])
    assert "geography_not_comparable" in result["growth_exclusion_reasons"]
    assert "not_growth_eligible" in result["headline_exclusion_reasons"]


def test_methodology_change_blocks_growth_without_rewriting_raw_value():
    frame = pd.DataFrame([stable_row(methodology_change=True, raw_value=49_999)])
    result = evaluate_city_data_fitness(frame).iloc[0]

    assert result["raw_value"] == 49_999
    assert not bool(result["growth_eligible"])
    assert "methodology_change" in result["growth_exclusion_reasons"]


def test_unknown_methodology_change_fails_growth_closed():
    result = evaluate_city_data_fitness(
        pd.DataFrame([stable_row(methodology_change="unknown")])
    ).iloc[0]

    assert not bool(result["growth_eligible"])
    assert not bool(result["headline_eligible"])
    assert "methodology_change_unknown" in result["growth_exclusion_reasons"]


def test_unrecognized_methodology_value_fails_growth_closed():
    result = evaluate_city_data_fitness(
        pd.DataFrame([stable_row(methodology_change="partial")])
    ).iloc[0]

    assert not bool(result["growth_eligible"])
    assert "methodology_change_unknown" in result["growth_exclusion_reasons"]


def test_unknown_administrative_reclassification_fails_growth_unless_harmonized():
    result = evaluate_city_data_fitness(
        pd.DataFrame([stable_row(administrative_reclassification="uncertain")])
    ).iloc[0]
    harmonized = evaluate_city_data_fitness(
        pd.DataFrame(
            [
                stable_row(
                    administrative_reclassification="uncertain",
                    concordance_status="harmonized_common_geography",
                    boundary_temporally_fixed=False,
                )
            ]
        )
    ).iloc[0]

    assert not bool(result["growth_eligible"])
    assert "administrative_reclassification_unknown" in result["growth_exclusion_reasons"]
    assert bool(harmonized["growth_eligible"])


def test_unknown_inconsistency_fails_all_analytical_uses_closed():
    result = evaluate_city_data_fitness(
        pd.DataFrame([stable_row(known_inconsistency="not_reviewed")])
    ).iloc[0]

    assert not bool(result["level_eligible"])
    assert not bool(result["growth_eligible"])
    assert not bool(result["spatial_eligible"])
    assert not bool(result["headline_eligible"])
    assert "known_inconsistency_unknown" in result["fitness_reasons"]


def test_unrecognized_inconsistency_value_fails_all_uses_closed():
    result = evaluate_city_data_fitness(
        pd.DataFrame([stable_row(known_inconsistency="maybe")])
    ).iloc[0]

    assert not bool(result["level_eligible"])
    assert not bool(result["growth_eligible"])
    assert not bool(result["spatial_eligible"])
    assert not bool(result["headline_eligible"])
    assert "known_inconsistency_unknown" in result["fitness_reasons"]


def test_explicit_clear_adverse_evidence_remains_eligible():
    result = evaluate_city_data_fitness(
        pd.DataFrame(
            [
                stable_row(
                    administrative_reclassification="no",
                    methodology_change="none",
                    known_inconsistency="absent",
                )
            ]
        )
    ).iloc[0]

    assert bool(result["level_eligible"])
    assert bool(result["growth_eligible"])
    assert bool(result["headline_eligible"])


def test_threshold_selection_exposure_blocks_headline_only():
    result = evaluate_city_data_fitness(
        pd.DataFrame([stable_row(truncation_exposure="material")])
    ).iloc[0]

    assert bool(result["growth_eligible"])
    assert not bool(result["headline_eligible"])
    assert "truncation_exposure" in result["headline_exclusion_reasons"]


def test_missing_truncation_exposure_fails_headline_closed():
    row = stable_row()
    row.pop("truncation_exposure")
    result = evaluate_city_data_fitness(pd.DataFrame([row])).iloc[0]

    assert bool(result["growth_eligible"])
    assert not bool(result["headline_eligible"])
    assert "missing_truncation_exposure" in result["headline_exclusion_reasons"]


def test_missing_survivorship_exposure_fails_headline_closed():
    row = stable_row(survivorship_exposure=None)
    result = evaluate_city_data_fitness(pd.DataFrame([row])).iloc[0]

    assert bool(result["growth_eligible"])
    assert not bool(result["headline_eligible"])
    assert "missing_survivorship_exposure" in result["headline_exclusion_reasons"]


def test_spatial_use_requires_validated_coordinates_and_network_geography():
    result = evaluate_city_data_fitness(
        pd.DataFrame(
            [stable_row(coordinates_validated=False, network_geography_validated=False)]
        )
    ).iloc[0]

    assert not bool(result["spatial_eligible"])
    assert "coordinates_not_validated" in result["spatial_exclusion_reasons"]
    assert "network_geography_not_validated" in result["spatial_exclusion_reasons"]
    assert bool(result["growth_eligible"])


def test_headline_sample_filters_ineligible_rows_and_preserves_reasons():
    frame = pd.DataFrame(
        [
            stable_row(city_id="keep"),
            stable_row(
                city_id="drop",
                concordance_status="unresolved",
                boundary_temporally_fixed=False,
                boundary_change_status="unresolved",
            ),
        ]
    )

    result = headline_sample(frame)

    assert result["city_id"].tolist() == ["keep"]
    assert "headline_eligible" in result.columns

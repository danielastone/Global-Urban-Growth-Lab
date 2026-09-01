import pandas as pd

from urban_growth.data_fitness import evaluate_city_data_fitness


def _row(**overrides):
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
    }
    row.update(overrides)
    return row


def test_unrecognized_truncation_exposure_fails_headline_closed():
    result = evaluate_city_data_fitness(
        pd.DataFrame([_row(truncation_exposure="moderate")])
    ).iloc[0]

    assert bool(result["growth_eligible"])
    assert not bool(result["headline_eligible"])
    assert "truncation_exposure_unknown" in result["headline_exclusion_reasons"]


def test_unrecognized_survivorship_exposure_fails_headline_closed():
    result = evaluate_city_data_fitness(
        pd.DataFrame([_row(survivorship_exposure="not_applicable")])
    ).iloc[0]

    assert bool(result["growth_eligible"])
    assert not bool(result["headline_eligible"])
    assert "survivorship_exposure_unknown" in result["headline_exclusion_reasons"]


def test_registered_exposure_vocabulary_retains_expected_semantics():
    low = evaluate_city_data_fitness(
        pd.DataFrame([_row(truncation_exposure="low", survivorship_exposure="low")])
    ).iloc[0]
    unknown = evaluate_city_data_fitness(
        pd.DataFrame([_row(truncation_exposure="unknown")])
    ).iloc[0]

    assert bool(low["headline_eligible"])
    assert not bool(unknown["headline_eligible"])
    assert "truncation_exposure" in unknown["headline_exclusion_reasons"]

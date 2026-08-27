import pandas as pd
import pytest

from urban_growth.crosswalk import accepted_crosswalk, validate_wup_ghsl_crosswalk
from urban_growth.io import SourceSchemaError


def sample_crosswalk() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "wup_city_id": [100, 101],
            "ghsl_city_id": [10, 10],
            "match_status": ["accepted", "accepted"],
            "match_method": ["point_in_polygon_name", "point_in_polygon_name"],
            "evidence": ["reviewed 2025 geometry", "reviewed 2025 geometry"],
        }
    )


def test_crosswalk_requires_explicit_many_to_one_rule() -> None:
    with pytest.raises(SourceSchemaError, match="aggregation rule"):
        accepted_crosswalk(sample_crosswalk())
    result = accepted_crosswalk(sample_crosswalk(), allow_many_to_one=True)
    assert result["wup_units_per_ghsl"].tolist() == [2, 2]


def test_crosswalk_rejects_multiple_accepted_targets_for_one_wup_city() -> None:
    crosswalk = sample_crosswalk()
    crosswalk.loc[1, "wup_city_id"] = 100
    crosswalk.loc[1, "ghsl_city_id"] = 11
    with pytest.raises(SourceSchemaError, match="multiple accepted"):
        validate_wup_ghsl_crosswalk(crosswalk)


def test_crosswalk_requires_evidence_for_accepted_match() -> None:
    crosswalk = sample_crosswalk().iloc[[0]].copy()
    crosswalk.loc[:, "evidence"] = None
    with pytest.raises(SourceSchemaError, match="require IDs, method, and evidence"):
        validate_wup_ghsl_crosswalk(crosswalk)

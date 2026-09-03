import pandas as pd

from urban_growth.japan_h1 import (
    add_lineage_ids,
    chronological_predictions,
    two_way_h1_contrasts,
)


def _denominator() -> pd.DataFrame:
    rows = []
    for origin in (2005, 2010, 2015):
        for index in range(12):
            recent = (index - 5) / 1_000
            rows.append(
                {
                    "locality_id": f"{origin}:city-{index}",
                    "lag_row_id": f"{origin - 5}:city-{index}",
                    "origin_row_id": f"{origin}:city-{index}",
                    "endpoint_row_id": f"{origin + 5}:city-{index}",
                    "period_start": origin,
                    "population_start": 30_000 + index * 2_000,
                    "recent_growth": recent,
                    "future_growth": recent,
                    "analysis_eligible": True,
                }
            )
    return pd.DataFrame(rows)


def test_chronological_predictions_use_only_prior_origins_and_common_rows() -> None:
    predictions = chronological_predictions(add_lineage_ids(_denominator()))
    assert set(predictions["origin"]) == {2010, 2015}
    assert set(predictions.loc[predictions["origin"].eq(2010), "train_origins"]) == {"2005"}
    assert set(predictions.loc[predictions["origin"].eq(2015), "train_origins"]) == {
        "2005;2010"
    }
    counts = predictions.groupby(["origin", "model"]).size().unstack()
    assert counts.nunique(axis=1).eq(1).all()


def test_two_way_gate_withholds_confidence_claim_with_two_origins() -> None:
    predictions = chronological_predictions(add_lineage_ids(_denominator()))
    contrasts = two_way_h1_contrasts(predictions, draws=200, seed=7)
    assert contrasts["rmse_relative_improvement"].gt(0).all()
    assert not contrasts["origin_cluster_inference_adequate"].any()
    assert not contrasts["registered_gate_pass"].any()
    assert contrasts["lineage_clusters"].eq(12).all()
    assert contrasts["origin_clusters"].eq(2).all()

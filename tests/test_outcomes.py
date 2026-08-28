import pandas as pd

from urban_growth.outcomes import add_decline_indicators, add_size_bins


def test_prespecified_decline_thresholds() -> None:
    result = add_decline_indicators(pd.DataFrame({"annual_growth": [-0.003, -0.006, -0.011]}))
    assert result["decline_25bp"].tolist() == [True, True, True]
    assert result["decline_50bp"].tolist() == [False, True, True]
    assert result["decline_100bp"].tolist() == [False, False, True]


def test_size_bins_preserve_50k_boundary() -> None:
    result = add_size_bins(pd.DataFrame({"population_start": [49_999, 50_000, 2_000_000]}))
    assert result["size_bin"].astype(str).tolist() == ["<50k", "50–150k", "2m+"]

import numpy as np
import pandas as pd
import pytest

from urban_growth.panel import PanelValidationError, add_annualized_log_growth, validate_panel


def sample_panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "city_id": ["A", "B"],
            "country_code": ["X", "Y"],
            "period_start": [2000, 2000],
            "period_end": [2005, 2010],
            "population_start": [100_000, 200_000],
            "population_end": [110_000, 180_000],
        }
    )


def test_annualized_log_growth_respects_interval_length() -> None:
    result = add_annualized_log_growth(sample_panel())
    assert result.loc[0, "annual_growth"] == pytest.approx(np.log(1.1) / 5)
    assert result.loc[1, "annual_growth"] == pytest.approx(np.log(0.9) / 10)


@pytest.mark.parametrize("column", ["population_start", "population_end"])
def test_nonpositive_population_fails(column: str) -> None:
    panel = sample_panel()
    panel.loc[0, column] = 0
    with pytest.raises(PanelValidationError, match="positive"):
        validate_panel(panel)


def test_duplicate_city_period_fails() -> None:
    panel = pd.concat([sample_panel(), sample_panel().iloc[[0]]], ignore_index=True)
    with pytest.raises(PanelValidationError, match="unique"):
        validate_panel(panel)

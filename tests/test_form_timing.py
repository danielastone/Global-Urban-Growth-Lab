import pandas as pd

from urban_growth.form_timing import build_form_timing_rows


def test_form_timing_separates_contemporaneous_and_lead_lag_rows() -> None:
    frame = pd.DataFrame(
        {
            "city_id": ["a", "a", "a"],
            "period_start": [2000, 2005, 2015],
            "period_end": [2005, 2010, 2020],
            "population_growth": [0.01, 0.02, 0.03],
            "form_change": [0.02, 0.03, 0.04],
        }
    )
    result = build_form_timing_rows(frame)
    assert len(result["C1"]) == 3
    assert result["C2"]["period_start"].tolist() == [2005]
    assert result["C3"]["period_start"].tolist() == [2005]
    assert result["C3"]["timing_specification"].eq("C3_form_leads_population").all()

import pandas as pd

from urban_growth.adapters.wup import city_population_panel


def test_verified_f21_header_contract() -> None:
    frame = pd.read_csv("tests/fixtures/wup_f21_schema.csv", dtype={"1975": float})
    result = city_population_panel(
        frame,
        city_id_column="City_Code",
        metadata_columns=[
            "LocID", "ISO3_Code", "City_Name", "PWCent_Longitude", "PWCent_Latitude"
        ],
    )
    assert result["city_id"].nunique() == 2
    assert result.loc[result["city_id"] == 10002, "year"].tolist() == [2050]

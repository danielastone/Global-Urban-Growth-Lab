import pandas as pd
import pytest

from urban_growth.adapters.ghsl_ucdb import indicator_panel
from urban_growth.adapters.wup import degree_of_urbanization_panel
from urban_growth.io import SourceSchemaError


def test_ghsl_indicator_preserves_boundary_mode() -> None:
    source = pd.DataFrame(
        {"ID": [1], "NAME": ["Example"], "MT_POP_TOT_1975": [100], "MT_POP_TOT_1980": [120]}
    )
    result = indicator_panel(
        source, city_id_column="ID", metadata_columns=["NAME"],
        indicator_pattern=r"MT_POP_TOT_(?P<year>\d{4})", value_name="population",
        boundary_mode="dynamic",
    )
    assert result["year"].tolist() == [1975, 1980]
    assert result["boundary_mode"].unique().tolist() == ["dynamic"]


def test_wup_converts_thousands_and_requires_mapped_categories() -> None:
    source = pd.DataFrame({"Code": [1], "Class": ["city"], "1975": [2.5], "1980": [3.0]})
    result = degree_of_urbanization_panel(
        source, location_id_column="Code", category_column="Class"
    )
    assert result["population"].tolist() == [2500.0, 3000.0]

    source.loc[0, "Class"] = "publisher label not mapped"
    with pytest.raises(SourceSchemaError, match="Unmapped"):
        degree_of_urbanization_panel(source, location_id_column="Code", category_column="Class")

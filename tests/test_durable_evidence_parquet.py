from pathlib import Path

import pandas as pd

from urban_growth.durable_evidence import PARQUET_MEDIA_TYPE, _output_dimensions


def test_output_dimensions_supports_parquet(tmp_path: Path):
    path = tmp_path / "evidence.parquet"
    pd.DataFrame({"city_id": [1, 2], "origin": [2000, 2005]}).to_parquet(path, index=False)

    assert _output_dimensions(path, PARQUET_MEDIA_TYPE) == (2, 2)

import pandas as pd
import pytest

from urban_growth.spi_evidence import load_spi, revision_diagnostic


def _write(tmp_path, rows):
    p = tmp_path / "spi.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return p


def test_preserves_pillars_dimensions_missingness_and_unmatched(tmp_path):
    p = _write(
        tmp_path,
        [
            {
                "iso3c": "USA",
                "date": 2024,
                "country": "United States",
                "SPI.D3.1.POV": 0,
                "SPI.D4.1.1.POPU": 1,
                "SPI.D5.1.DILG": None,
            },
            {
                "iso3c": "XKX",
                "date": 2024,
                "country": "Kosovo",
                "SPI.D3.1.POV": 0.5,
                "SPI.D4.1.1.POPU": 0.5,
                "SPI.D5.1.DILG": 0.5,
            },
        ],
    )
    x = load_spi(p, release="r")
    assert set(x.pillar_id) == {"SPI.PIL3", "SPI.PIL4", "SPI.PIL5"}
    assert x.loc[x.indicator_id.eq("SPI.D4.1.1.POPU"), "dimension_id"].eq("SPI.DIM4.1").all()
    assert x.source_missing.sum() == 1
    assert x.loc[x.iso3c.eq("XKX"), "country_id"].isna().all()


def test_fails_closed_on_duplicates_bounds_and_malformed(tmp_path):
    base = {"iso3c": "USA", "date": 2024, "country": "US", "SPI.D3.1.POV": 0.5}
    with pytest.raises(ValueError, match="duplicate"):
        load_spi(_write(tmp_path, [base, base]), release="r")
    with pytest.raises(ValueError, match="outside"):
        load_spi(_write(tmp_path, [{**base, "SPI.D3.1.POV": 2}]), release="r")
    with pytest.raises(ValueError, match="nonnumeric"):
        load_spi(_write(tmp_path, [{**base, "SPI.D3.1.POV": "bad"}]), release="r")


def test_revision_diagnostic_counts_changes(tmp_path):
    a = load_spi(
        _write(tmp_path, [{"iso3c": "USA", "date": 2024, "country": "US", "SPI.D3.1.POV": 0.5}]),
        release="a",
    )
    b = a.copy()
    b["value"] = 0.6
    assert revision_diagnostic(a, b)["changed_cells"] == 1

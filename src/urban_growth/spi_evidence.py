"""Pinned World Bank SPI evidence ingestion without composite scoring."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

INDICATOR = re.compile(r"^SPI\.D([345])\.(.+)$")
PILLAR_KIND = {"3": "product_availability", "4": "production_sources", "5": "production_capacity"}


def load_spi(
    path: str | Path, *, release: str, unresolved_codes: set[str] = frozenset({"XKX"})
) -> pd.DataFrame:
    wide = pd.read_csv(path, encoding="utf-8-sig", na_values=["NA"])
    required = {"iso3c", "date", "country"}
    if not required.issubset(wide):
        raise ValueError(f"SPI source missing columns: {sorted(required - set(wide))}")
    if wide.duplicated(["iso3c", "date"]).any():
        raise ValueError("SPI source has duplicate economy-year rows")
    indicators = [c for c in wide if INDICATOR.fullmatch(c)]
    if not indicators:
        raise ValueError("SPI source has no selected pillar indicators")
    long = wide.melt(
        id_vars=["iso3c", "date", "country"],
        value_vars=indicators,
        var_name="indicator_id",
        value_name="value",
    )
    numeric = pd.to_numeric(long.value, errors="coerce")
    malformed = long.value.notna() & numeric.isna()
    if malformed.any():
        raise ValueError("SPI source contains nonnumeric indicator values")
    if ((numeric.dropna() < 0) | (numeric.dropna() > 1)).any():
        raise ValueError("SPI indicator value outside [0, 1]")
    parsed = long.indicator_id.str.extract(INDICATOR)
    long["pillar_id"] = "SPI.PIL" + parsed[0]
    long["dimension_id"] = "SPI.DIM" + parsed[0] + "." + parsed[1].str.split(".").str[0]
    long["interpretation"] = parsed[0].map(PILLAR_KIND)
    long["spi_observation_year"] = pd.to_numeric(long.pop("date"), downcast="integer")
    long["spi_release"] = release
    long["source_missing"] = numeric.isna()
    long["value"] = numeric
    long["country_id"] = long.iso3c.mask(long.iso3c.isin(unresolved_codes))
    long["crosswalk_status"] = long.iso3c.map(
        lambda x: "unresolved" if x in unresolved_codes else "direct_source_iso3"
    )
    return long[
        [
            "country_id",
            "iso3c",
            "country",
            "spi_release",
            "spi_observation_year",
            "pillar_id",
            "dimension_id",
            "indicator_id",
            "interpretation",
            "value",
            "source_missing",
            "crosswalk_status",
        ]
    ]


def revision_diagnostic(current: pd.DataFrame, prior: pd.DataFrame) -> dict[str, int]:
    keys = ["iso3c", "spi_observation_year", "indicator_id"]
    a = current.set_index(keys).value
    b = prior.set_index(keys).value
    common = a.index.intersection(b.index)
    changed = a.loc[common].fillna(-999999) != b.loc[common].fillna(-999999)
    return {
        "common_cells": len(common),
        "changed_cells": int(changed.sum()),
        "current_only_cells": len(a.index.difference(b.index)),
        "prior_only_cells": len(b.index.difference(a.index)),
    }


def coverage_diagnostic(data: pd.DataFrame) -> pd.DataFrame:
    return data.groupby(["pillar_id", "spi_observation_year"], as_index=False).agg(
        economies=("iso3c", "nunique"),
        observed=("value", "count"),
        cells=("value", "size"),
        unmatched=("country_id", lambda x: int(x.isna().sum())),
    )


def pairwise_indicator_correlations(data: pd.DataFrame) -> pd.DataFrame:
    latest = int(data.spi_observation_year.max())
    wide = data[data.spi_observation_year.eq(latest)].pivot(
        index="iso3c", columns="indicator_id", values="value"
    )
    matrix = wide.corr(min_periods=20).rename_axis(index="indicator_id_1", columns="indicator_id_2")
    corr = matrix.stack().rename("correlation").reset_index()
    return corr[corr.indicator_id_1 < corr.indicator_id_2]

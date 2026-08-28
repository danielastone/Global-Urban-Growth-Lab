"""Schema-driven conversion of wide year attributes to a long panel."""

from __future__ import annotations

import re

import pandas as pd

from urban_growth.io import SourceSchemaError, require_columns


def wide_years_to_long(
    frame: pd.DataFrame,
    *,
    id_columns: list[str],
    value_pattern: str,
    value_name: str,
    year_group: str = "year",
) -> pd.DataFrame:
    """Reshape only columns matching a declared regex with a named year group."""
    require_columns(frame, set(id_columns), source_name="wide source")
    pattern = re.compile(value_pattern)
    matched: list[tuple[str, int]] = []
    for column in frame.columns:
        match = pattern.fullmatch(str(column))
        if match:
            if year_group not in match.groupdict():
                raise SourceSchemaError(f"Pattern must define named group '{year_group}'")
            matched.append((column, int(match.group(year_group))))
    if not matched:
        raise SourceSchemaError("No columns matched the declared year pattern")
    years = [year for _, year in matched]
    if len(years) != len(set(years)):
        raise SourceSchemaError("Multiple columns resolve to the same year")
    subset = frame[id_columns + [column for column, _ in matched]].copy()
    rename = {column: year for column, year in matched}
    subset = subset.rename(columns=rename)
    long = subset.melt(id_vars=id_columns, var_name="year", value_name=value_name)
    long["year"] = long["year"].astype(int)
    return long.sort_values(id_columns + ["year"]).reset_index(drop=True)

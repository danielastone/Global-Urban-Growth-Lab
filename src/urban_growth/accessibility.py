"""Modern-period accessibility exposure construction."""

from __future__ import annotations

import pandas as pd

from urban_growth.io import SourceSchemaError, require_columns

TRAVEL_TIME_BANDS = ((0, 1), (1, 2), (2, 4), (4, 8))


def mutually_exclusive_rival_mass(
    pairs: pd.DataFrame,
    *,
    nominal_vintage: int,
    focal_column: str = "focal_city_id",
    travel_time_column: str = "travel_time_hours",
    rival_population_column: str = "rival_population",
) -> pd.DataFrame:
    """Aggregate other-centre mass into non-overlapping 0-1/1-2/2-4/4-8h bands."""
    require_columns(
        pairs,
        {focal_column, "rival_city_id", travel_time_column, rival_population_column},
        source_name="accessibility pairs",
    )
    if nominal_vintage < 2000:
        raise SourceSchemaError("Accessibility is a modern validation module, not a long panel")
    if (pairs[focal_column] == pairs["rival_city_id"]).any():
        raise SourceSchemaError("Rival mass must exclude the focal city")
    if pairs[[travel_time_column, rival_population_column]].isna().any().any():
        raise SourceSchemaError("Accessibility pairs cannot contain missing time or mass")
    if (pairs[[travel_time_column, rival_population_column]] < 0).any().any():
        raise SourceSchemaError("Travel time and rival population cannot be negative")
    result = pd.DataFrame(index=pd.Index(pairs[focal_column].drop_duplicates(), name=focal_column))
    for lower, upper in TRAVEL_TIME_BANDS:
        mask = pairs[travel_time_column].ge(lower) & pairs[travel_time_column].lt(upper)
        mass = pairs.loc[mask].groupby(focal_column)[rival_population_column].sum()
        result[f"rival_mass_{lower}_{upper}h"] = mass.reindex(result.index, fill_value=0.0)
    result["accessibility_nominal_vintage"] = nominal_vintage
    result["band_definition"] = "mutually_exclusive_left_closed"
    return result.reset_index()

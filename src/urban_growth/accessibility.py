"""Modern-period accessibility exposure construction."""

from __future__ import annotations

import pandas as pd

from urban_growth.io import SourceSchemaError, require_columns

TRAVEL_TIME_BANDS = ((0, 1), (1, 2), (2, 4), (4, 8))


def _validate_accessibility_pairs(
    pairs: pd.DataFrame,
    *,
    nominal_vintage: int,
    focal_column: str,
    travel_time_column: str,
    rival_population_column: str,
) -> None:
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


def mutually_exclusive_rival_mass(
    pairs: pd.DataFrame,
    *,
    nominal_vintage: int,
    focal_column: str = "focal_city_id",
    travel_time_column: str = "travel_time_hours",
    rival_population_column: str = "rival_population",
) -> pd.DataFrame:
    """Aggregate other-centre mass into non-overlapping 0-1/1-2/2-4/4-8h bands."""
    _validate_accessibility_pairs(
        pairs,
        nominal_vintage=nominal_vintage,
        focal_column=focal_column,
        travel_time_column=travel_time_column,
        rival_population_column=rival_population_column,
    )
    result = pd.DataFrame(index=pd.Index(pairs[focal_column].drop_duplicates(), name=focal_column))
    for lower, upper in TRAVEL_TIME_BANDS:
        mask = pairs[travel_time_column].ge(lower) & pairs[travel_time_column].lt(upper)
        mass = pairs.loc[mask].groupby(focal_column)[rival_population_column].sum()
        result[f"rival_mass_{lower}_{upper}h"] = mass.reindex(result.index, fill_value=0.0)
    result["accessibility_nominal_vintage"] = nominal_vintage
    result["band_definition"] = "mutually_exclusive_left_closed"
    return result.reset_index()


def border_conditioned_rival_mass(
    pairs: pd.DataFrame,
    city_country_lookup: pd.DataFrame,
    *,
    nominal_vintage: int,
    focal_column: str = "focal_city_id",
    travel_time_column: str = "travel_time_hours",
    rival_population_column: str = "rival_population",
    lookup_city_column: str = "city_id",
    country_column: str = "country_code",
) -> pd.DataFrame:
    """Construct descriptive same-country and cross-border rival-mass exposures.

    Country assignments must be validated upstream; no boundary geometry is interpreted here.
    Downstream coefficient signs alone do not identify competition versus agglomeration.
    """
    _validate_accessibility_pairs(
        pairs,
        nominal_vintage=nominal_vintage,
        focal_column=focal_column,
        travel_time_column=travel_time_column,
        rival_population_column=rival_population_column,
    )
    require_columns(
        city_country_lookup,
        {lookup_city_column, country_column},
        source_name="city-country lookup",
    )
    if city_country_lookup[lookup_city_column].duplicated().any():
        raise SourceSchemaError("City-country lookup must contain unique city IDs")
    if city_country_lookup[[lookup_city_column, country_column]].isna().any().any():
        raise SourceSchemaError("City-country lookup cannot contain missing IDs or country codes")

    country_codes = city_country_lookup[country_column].astype("string")
    if country_codes.str.strip().eq("").any():
        raise SourceSchemaError("City-country lookup cannot contain blank country codes")
    if country_codes.ne(country_codes.str.strip()).any():
        raise SourceSchemaError("City-country lookup country codes cannot contain outer whitespace")

    lookup = city_country_lookup[[lookup_city_column, country_column]].copy()
    lookup[country_column] = country_codes
    focal_lookup = lookup.rename(
        columns={lookup_city_column: focal_column, country_column: "_focal_country_code"}
    )
    rival_lookup = lookup.rename(
        columns={lookup_city_column: "rival_city_id", country_column: "_rival_country_code"}
    )
    input_row_count = len(pairs)
    joined = pairs.merge(focal_lookup, on=focal_column, how="left", validate="many_to_one")
    joined = joined.merge(rival_lookup, on="rival_city_id", how="left", validate="many_to_one")
    if len(joined) != input_row_count:
        raise SourceSchemaError("City-country joins changed the accessibility-pair row count")
    if joined[["_focal_country_code", "_rival_country_code"]].isna().any().any():
        raise SourceSchemaError("Every focal and rival city must match the city-country lookup")

    base = mutually_exclusive_rival_mass(
        joined,
        nominal_vintage=nominal_vintage,
        focal_column=focal_column,
        travel_time_column=travel_time_column,
        rival_population_column=rival_population_column,
    )
    result = base.set_index(focal_column)
    same_country = joined["_focal_country_code"].eq(joined["_rival_country_code"])

    for lower, upper in TRAVEL_TIME_BANDS:
        in_band = joined[travel_time_column].ge(lower) & joined[travel_time_column].lt(upper)
        band_column = f"rival_mass_{lower}_{upper}h"
        for suffix, border_mask in (
            ("same_country", same_country),
            ("cross_border", ~same_country),
        ):
            mass = (
                joined.loc[in_band & border_mask]
                .groupby(focal_column)[rival_population_column]
                .sum()
            )
            result[f"{band_column}_{suffix}"] = mass.reindex(
                result.index, fill_value=0.0
            )
    result["border_definition"] = "country_code_equality"
    return result.reset_index()

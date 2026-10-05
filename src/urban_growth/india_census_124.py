"""Qualification gate for an India direct-count benchmark under issue #124."""

from __future__ import annotations

import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

REQUIRED = {
    "candidate_id",
    "official_source",
    "waves",
    "direct_locality_counts",
    "origin_denominator_available",
    "future_membership_conditioned",
    "official_adjacent_wave_concordance",
    "usable_forecast_origins",
    "release_status",
}


def india_issue_124_source_register() -> pd.DataFrame:
    """Return the registered official-source candidates and known identification limits."""
    return pd.DataFrame(
        [
            {
                "candidate_id": "india_a04_2011_historical_town_series",
                "official_source": "Census of India 2011 A-04 population-class tables",
                "waves": "1981;1991;2001;2011",
                "direct_locality_counts": True,
                "origin_denominator_available": False,
                "future_membership_conditioned": True,
                "official_adjacent_wave_concordance": False,
                "usable_forecast_origins": 0,
                "release_status": "released",
                "qualification_note": (
                    "Historical columns are published for the 2011 town/class frame; "
                    "they cannot define 1981 or 1991 origin cohorts before later survival and size"
                ),
            },
            {
                "candidate_id": "india_pca_lcd_2001_2011",
                "official_source": (
                    "Census of India 2001/2011 Primary Census Abstract and Location Code Directory"
                ),
                "waves": "2001;2011",
                "direct_locality_counts": True,
                "origin_denominator_available": True,
                "future_membership_conditioned": False,
                "official_adjacent_wave_concordance": True,
                "usable_forecast_origins": 0,
                "release_status": "released",
                "qualification_note": (
                    "One historical transition can audit coverage and growth, but two waves "
                    "cannot form a recent-growth predictor and later outcome"
                ),
            },
            {
                "candidate_id": "india_original_town_directories_1981_2011",
                "official_source": "Census of India original state town directories",
                "waves": "1981;1991;2001;2011",
                "direct_locality_counts": True,
                "origin_denominator_available": True,
                "future_membership_conditioned": False,
                "official_adjacent_wave_concordance": False,
                "usable_forecast_origins": 0,
                "release_status": "released_fragmented",
                "qualification_note": (
                    "Potential multi-origin source, but no registered national official crosswave "
                    "town concordance currently resolves births, declassifications, splits, and merges"
                ),
            },
            {
                "candidate_id": "india_census_2027_locality_outputs",
                "official_source": "Census of India 2027 locality outputs and concordances",
                "waves": "2001;2011;2027",
                "direct_locality_counts": True,
                "origin_denominator_available": False,
                "future_membership_conditioned": False,
                "official_adjacent_wave_concordance": False,
                "usable_forecast_origins": 0,
                "release_status": "not_released",
                "qualification_note": (
                    "The census reference date is scheduled for 2027; locality outputs and "
                    "crosswave concordances do not yet exist"
                ),
            },
        ]
    )


def qualify_india_issue_124_sources(register: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate candidates without allowing future-defined membership to pass."""
    require_columns(register, REQUIRED, source_name="India issue 124 source register")
    reject_duplicate_keys(register, ["candidate_id"], source_name="India issue 124 source register")
    out = register.copy()
    for column in [
        "direct_locality_counts",
        "origin_denominator_available",
        "future_membership_conditioned",
        "official_adjacent_wave_concordance",
    ]:
        if out[column].isna().any():
            raise SourceSchemaError(f"India source register has unknown {column}")
        out[column] = out[column].astype(bool)
    out["usable_forecast_origins"] = pd.to_numeric(
        out["usable_forecast_origins"], errors="coerce"
    )
    if out["usable_forecast_origins"].isna().any():
        raise SourceSchemaError("India source register has invalid usable forecast-origin counts")

    out["issue_124_qualified"] = (
        out["direct_locality_counts"]
        & out["origin_denominator_available"]
        & ~out["future_membership_conditioned"]
        & out["official_adjacent_wave_concordance"]
        & out["usable_forecast_origins"].ge(2)
        & out["release_status"].eq("released")
    )
    out["exclusion_reason"] = "qualified"
    out.loc[~out["direct_locality_counts"], "exclusion_reason"] = "not_direct_locality_counts"
    out.loc[~out["origin_denominator_available"], "exclusion_reason"] = (
        "origin_denominator_unavailable"
    )
    out.loc[out["future_membership_conditioned"], "exclusion_reason"] = (
        "future_conditioned_town_universe"
    )
    out.loc[
        out["origin_denominator_available"]
        & ~out["future_membership_conditioned"]
        & ~out["official_adjacent_wave_concordance"],
        "exclusion_reason",
    ] = "official_crosswave_concordance_unresolved"
    out.loc[
        out["origin_denominator_available"]
        & ~out["future_membership_conditioned"]
        & out["official_adjacent_wave_concordance"]
        & out["usable_forecast_origins"].lt(2),
        "exclusion_reason",
    ] = "insufficient_forecast_origins"
    out.loc[out["release_status"].eq("not_released"), "exclusion_reason"] = (
        "official_locality_outputs_not_released"
    )

    qualified = out["issue_124_qualified"]
    status = pd.DataFrame(
        [
            {
                "issue": 124,
                "pilot": "India Census towns",
                "candidate_sources": len(out),
                "qualified_sources": int(qualified.sum()),
                "benchmark_estimable": bool(qualified.any()),
                "h1_independent_confirmation": False,
                "historical_2001_2011_transition_permitted": True,
                "historical_transition_closes_issue_124": False,
                "decision": (
                    "ready_for_matched_benchmark"
                    if qualified.any()
                    else "unresolved_no_origin_valid_multiwave_concorded_town_panel"
                ),
            }
        ]
    )
    return out, status

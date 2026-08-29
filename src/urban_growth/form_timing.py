"""Timing-safe data preparation for population and urban-form lead-lag tests."""

from __future__ import annotations

import pandas as pd

from urban_growth.io import SourceSchemaError, require_columns


def build_form_timing_rows(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return the locked C1, C2 and C3 samples without implying causality.

    C1 is contemporaneous association. C2 tests population growth in the prior
    interval against later form change. C3 reverses that lead-lag ordering.
    """
    required = {"city_id", "period_start", "period_end", "population_growth", "form_change"}
    require_columns(frame, required, source_name="form timing panel")
    if frame.duplicated(["city_id", "period_start", "period_end"]).any():
        raise SourceSchemaError("Form timing panel keys must be unique")
    ordered = frame.sort_values(["city_id", "period_start", "period_end"]).copy()
    group = ordered.groupby("city_id", sort=False)
    ordered["prior_period_end"] = group["period_end"].shift()
    ordered["prior_population_growth"] = group["population_growth"].shift()
    ordered["prior_form_change"] = group["form_change"].shift()
    adjacent = ordered["prior_period_end"].eq(ordered["period_start"])
    c1 = ordered.copy()
    c1["timing_specification"] = "C1_contemporaneous"
    c2 = ordered.loc[adjacent & ordered["prior_population_growth"].notna()].copy()
    c2["timing_specification"] = "C2_population_leads_form"
    c3 = ordered.loc[adjacent & ordered["prior_form_change"].notna()].copy()
    c3["timing_specification"] = "C3_form_leads_population"
    return {"C1": c1, "C2": c2, "C3": c3}

import pandas as pd
import pytest

from urban_growth.construction_smoothing import compare_direct_counts_with_ghsl
from urban_growth.io import SourceSchemaError


def panel(source: str, boundary: str, scale: float = 1.0) -> pd.DataFrame:
    rows = []
    for origin, pairs in [(2000, [(0.01, 0.02), (0.03, -0.01)]), (2010, [(0.02, 0.03), (-0.01, -0.02)])]:
        for index, (recent, future) in enumerate(pairs):
            rows.append({
                "country_code": "USA", "locality_id": f"p{index}", "period_start": origin,
                "source": source, "recent_growth": recent * scale, "future_growth": future * scale,
                "analysis_eligible": not (origin == 2000 and index == 1),
                "concordance_quality": "official_one_to_one", "census_recency_years": 0,
                "boundary_mode": boundary,
            })
    return pd.DataFrame(rows)


def test_comparison_preserves_denominators_and_produces_required_contrasts() -> None:
    coverage, metrics, contrasts = compare_direct_counts_with_ghsl(
        panel("direct_count", "official_dynamic"), panel("ghsl_fixed", "fixed_2025", 0.8)
    )
    direct_coverage = coverage.loc[coverage["source"].eq("direct_count")].iloc[0]
    assert direct_coverage["origin_denominator_rows"] == 4
    assert direct_coverage["unresolved_rows"] == 1
    assert {"persistence_beta", "persistence_mae", "sign_reversal_rate", "mean_growth_curvature"} <= set(metrics)
    assert "persistence_beta_ghsl_minus_direct" in contrasts


def test_single_origin_fails_closed() -> None:
    direct = panel("direct_count", "official_dynamic").query("period_start == 2010")
    ghsl = panel("ghsl_fixed", "fixed_2025").query("period_start == 2010")
    with pytest.raises(SourceSchemaError, match="1 matched forecast origins"):
        compare_direct_counts_with_ghsl(direct, ghsl)


def test_future_only_entrant_cannot_expand_direct_denominator() -> None:
    direct = panel("direct_count", "official_dynamic")
    ghsl = panel("ghsl_fixed", "fixed_2025")
    entrant = ghsl.iloc[[0]].assign(locality_id="future-entrant")
    coverage, metrics, _ = compare_direct_counts_with_ghsl(direct, pd.concat([ghsl, entrant]))
    assert coverage.loc[coverage["source"].eq("ghsl_fixed"), "origin_denominator_rows"].iloc[0] == 5
    assert metrics["matched_analysis_rows"].max() == 3

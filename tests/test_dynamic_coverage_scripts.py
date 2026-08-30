from pathlib import Path

import pandas as pd
import pytest

from urban_growth.dynamic_estimators import check_coverage_gate, combine_coverage_artifacts
from urban_growth.io import SourceSchemaError


def write_coverage_cells(directory: Path, *, failing_cell: tuple[float, int] | None = None) -> None:
    for persistence in (0.2, 0.6, 0.9):
        for panel_length in (6, 8, 10):
            rows = []
            for estimator in ("pooled_dynamic", "city_fe_dynamic", "half_panel_jackknife"):
                eligible = estimator == "half_panel_jackknife"
                passed = eligible and (persistence, panel_length) != failing_cell
                rows.append(
                    {
                        "persistence": persistence,
                        "panel_length": panel_length,
                        "estimator_id": estimator,
                        "production_design": True,
                        "coverage_gate_eligible": eligible,
                        "coverage_gate_pass": passed if eligible else pd.NA,
                    }
                )
            tag = f"{str(persistence).replace('.', '')}_{panel_length}"
            pd.DataFrame(rows).to_csv(
                directory / f"dynamic_bootstrap_coverage_{tag}.csv", index=False
            )


def test_combiner_validates_complete_grid_and_gate_pass(tmp_path: Path) -> None:
    write_coverage_cells(tmp_path)
    result = combine_coverage_artifacts(tmp_path)
    assert len(result) == 27
    check_coverage_gate(result)


def test_gate_reports_failed_corrected_cell(tmp_path: Path) -> None:
    write_coverage_cells(tmp_path, failing_cell=(0.9, 6))
    result = combine_coverage_artifacts(tmp_path)
    with pytest.raises(SourceSchemaError, match=r"rho=0.9, T=6"):
        check_coverage_gate(result)

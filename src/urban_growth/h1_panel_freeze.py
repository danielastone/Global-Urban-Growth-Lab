"""Blind H1 panel-freeze builder for preregistered fence PR A.

This module constructs and hashes the eligible H1 scoring panel without fitting
B0/B1, computing errors, producing performance summaries, evaluating gates, or
registering result nodes. It exists specifically to keep PR A outcome-blind.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from urban_growth.adapters.wup import read_f21_city_population
from urban_growth.h1_oos import (
    PROTOCOL,
    SOURCE_ID,
    SPEC_VERSION,
    WUP_VINTAGE,
    attach_strict_country_peer_growth,
    build_five_year_intervals,
    derive_eligible_origins,
)
from urban_growth.io import SourceSchemaError, reject_duplicate_keys

FORBIDDEN_PR_A_COLUMNS = frozenset(
    {
        "b0_prediction",
        "b1_prediction",
        "b0_error",
        "b1_error",
        "b0_absolute_error",
        "b1_absolute_error",
        "b0_squared_error",
        "b1_squared_error",
        "b0_rmse",
        "b1_rmse",
        "b0_mae",
        "b1_mae",
        "rmse",
        "mae",
        "relative_rmse_improvement",
        "mae_difference",
        "gate_passed",
        "winner",
    }
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def freeze_scoring_panel(
    intervals: pd.DataFrame,
    *,
    construction_commit: str,
    panel_spec_version: str = SPEC_VERSION,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Freeze eligible scoring rows without fitting either forecast model."""
    eligibility = derive_eligible_origins(intervals)
    eligible_origins = eligibility.loc[
        eligibility["eligible"], "origin"
    ].astype(int).tolist()
    if not eligible_origins:
        raise SourceSchemaError(
            "No origins pass the frozen 100-row/30-country training gate"
        )

    needed = [
        "future_growth",
        "country_peer_recent_growth_loo",
        "focal_city_recent_growth_deviation",
    ]
    rows: list[pd.DataFrame] = []
    for origin in eligible_origins:
        train = intervals.loc[intervals["period_end"] <= origin].copy()
        test = intervals.loc[intervals["period_start"] == origin].copy()
        train = train.dropna(subset=needed)
        test = test.dropna(subset=needed)
        train = train.loc[np.isfinite(train[needed]).all(axis=1)]
        test = test.loc[np.isfinite(test[needed]).all(axis=1)]

        if len(train) < PROTOCOL.minimum_training_rows:
            raise SourceSchemaError(
                "Eligible origin lost rows after frozen joint B0/B1 matching"
            )
        if train["country_code"].nunique() < PROTOCOL.minimum_training_countries:
            raise SourceSchemaError(
                "Eligible origin lost countries after frozen joint B0/B1 matching"
            )
        if test.empty:
            raise SourceSchemaError("Eligible origin has no jointly matched scoring rows")

        out = test.copy()
        out["training_rows"] = len(train)
        out["training_countries"] = int(train["country_code"].nunique())
        out["training_max_period_end"] = int(train["period_end"].max())
        out["training_precedes_or_equals_origin"] = (
            out["training_max_period_end"] <= origin
        )
        out["b0_b1_training_rows_identical"] = True
        out["b0_b1_scoring_rows_identical"] = True
        out["wup_vintage"] = WUP_VINTAGE
        out["construction_commit"] = construction_commit
        out["panel_spec_version"] = panel_spec_version
        rows.append(out)

    panel = pd.concat(rows, ignore_index=True)
    reject_duplicate_keys(
        panel,
        ["city_id", "period_start"],
        source_name="H1 OOS frozen scoring panel",
    )
    if not panel["training_precedes_or_equals_origin"].all():
        raise SourceSchemaError("H1 OOS training leakage detected during panel freeze")
    forbidden_present = sorted(FORBIDDEN_PR_A_COLUMNS.intersection(panel.columns))
    if forbidden_present:
        raise SourceSchemaError(
            "PR A frozen panel contains prohibited performance columns: "
            + ", ".join(forbidden_present)
        )
    return (
        panel.sort_values(["period_start", "country_code", "city_id"]).reset_index(
            drop=True
        ),
        eligibility,
    )


def panel_diagnostics(panel: pd.DataFrame, eligibility: pd.DataFrame) -> dict[str, Any]:
    """Return only fence-permitted diagnostics for acceptance review."""
    forbidden_present = sorted(FORBIDDEN_PR_A_COLUMNS.intersection(panel.columns))
    rows: list[dict[str, Any]] = []
    for origin in sorted(set(panel["period_start"])):
        group = panel.loc[panel["period_start"] == origin].copy()
        country_count = int(group["country_code"].nunique())
        country_sizes = group.groupby("country_code")["city_id"].transform("size")
        country_balanced = 1.0 / (country_count * country_sizes)
        row_weighted = pd.Series(1.0 / len(group), index=group.index)
        rows.append(
            {
                "origin": int(origin),
                "scoring_rows": int(len(group)),
                "scoring_countries": country_count,
                "training_rows": int(group["training_rows"].iloc[0]),
                "training_countries": int(group["training_countries"].iloc[0]),
                "training_max_period_end": int(group["training_max_period_end"].iloc[0]),
                "training_precedes_or_equals_origin": bool(
                    group["training_precedes_or_equals_origin"].all()
                ),
                "paired_training_rows": bool(
                    group["b0_b1_training_rows_identical"].all()
                ),
                "paired_scoring_rows": bool(
                    group["b0_b1_scoring_rows_identical"].all()
                ),
                "country_balanced_weight_sum": float(country_balanced.sum()),
                "country_balanced_weight_min": float(country_balanced.min()),
                "country_balanced_weight_max": float(country_balanced.max()),
                "row_weighted_weight_sum": float(row_weighted.sum()),
                "row_weighted_weight_min": float(row_weighted.min()),
                "row_weighted_weight_max": float(row_weighted.max()),
            }
        )

    required_lineage = {
        "wup_vintage",
        "period_start",
        "period_end",
        "horizon_years",
        "growth_window_years",
        "construction_commit",
        "panel_spec_version",
    }
    return {
        "panel_spec_version": SPEC_VERSION,
        "eligible_origins": eligibility.loc[
            eligibility["eligible"], "origin"
        ].astype(int).tolist(),
        "origin_diagnostics": rows,
        "schema_checks": {
            "required_lineage_columns_present": required_lineage.issubset(panel.columns),
            "forbidden_performance_columns_present": forbidden_present,
            "duplicate_city_origin_rows": int(
                panel.duplicated(["city_id", "period_start"]).sum()
            ),
        },
        "leakage_assertions": {
            "all_training_precedes_or_equals_origin": bool(
                panel["training_precedes_or_equals_origin"].all()
            ),
            "all_country_peer_leave_city_out": bool(
                panel["country_peer_leave_city_out"].all()
            ),
            "no_country_peer_future_use": bool(
                (~panel["country_peer_uses_future_value"]).all()
            ),
        },
    }


def write_panel_freeze_package(
    f21_path: Path,
    output_dir: Path,
    *,
    construction_commit: str,
    repo_root: Path,
) -> dict[str, Any]:
    """Write only PR A-permitted panel-freeze artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    city = read_f21_city_population(str(f21_path))
    intervals = build_five_year_intervals(city)
    strict, exclusions = attach_strict_country_peer_growth(intervals)
    panel, eligibility = freeze_scoring_panel(
        strict,
        construction_commit=construction_commit,
    )
    diagnostics = panel_diagnostics(panel, eligibility)

    panel_path = output_dir / "h1_oos_frozen_panel.parquet"
    eligibility_path = output_dir / "h1_oos_origin_eligibility.csv"
    exclusions_path = output_dir / "h1_oos_singleton_exclusions.csv"
    diagnostics_path = output_dir / "h1_oos_panel_diagnostics.json"
    manifest_path = output_dir / "h1_oos_panel_freeze_manifest.json"

    try:
        panel.to_parquet(panel_path, index=False)
    except (ImportError, ModuleNotFoundError) as exc:
        raise SourceSchemaError(
            "Parquet output requires an installed pandas parquet engine"
        ) from exc
    eligibility.to_csv(eligibility_path, index=False)
    exclusions.to_csv(exclusions_path, index=False)
    diagnostics_path.write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lock_path = repo_root / "uv.lock"
    generated_at = datetime.now(UTC).isoformat()
    manifest: dict[str, Any] = {
        "panel_spec_version": SPEC_VERSION,
        "source_id": SOURCE_ID,
        "wup_vintage": WUP_VINTAGE,
        "source_path": str(f21_path),
        "source_sha256": _sha256(f21_path),
        "construction_commit": construction_commit,
        "environment_lock": "uv.lock",
        "environment_lock_sha256": _sha256(lock_path),
        "construction_command": (
            "python -m urban_growth.h1_panel_freeze build "
            f"--f21 {f21_path} --output-dir {output_dir} "
            f"--commit {construction_commit} --repo-root {repo_root}"
        ),
        "generated_at": generated_at,
        "protocol": asdict(PROTOCOL),
        "eligible_origins": diagnostics["eligible_origins"],
        "panel_path": str(panel_path),
        "panel_sha256": _sha256(panel_path),
        "origin_eligibility_path": str(eligibility_path),
        "origin_eligibility_sha256": _sha256(eligibility_path),
        "singleton_exclusions_path": str(exclusions_path),
        "singleton_exclusions_sha256": _sha256(exclusions_path),
        "panel_diagnostics_path": str(diagnostics_path),
        "panel_diagnostics_sha256": _sha256(diagnostics_path),
        "performance_evaluation_performed": False,
        "result_nodes_registered": False,
        "fence_stage": "pr_a_panel_freeze",
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the blind H1 WUP panel-freeze package for PR A"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--f21", required=True, type=Path)
    build.add_argument("--output-dir", required=True, type=Path)
    build.add_argument("--commit", required=True)
    build.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "build":
        manifest = write_panel_freeze_package(
            args.f21,
            args.output_dir,
            construction_commit=args.commit,
            repo_root=args.repo_root,
        )
        print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

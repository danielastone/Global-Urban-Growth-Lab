"""One-shot registration helper for the validated H1 PR B archive."""

from __future__ import annotations

import csv
import json
from pathlib import Path

PACKAGE_ID = "wup-h1-oos-v1"
PARQUET_SHA = "a2e0782b7adf5bc20e606834ed41265b0108ce00b16d8096dc1a2aac189ab73a"
SUMMARY_SHA = "b0528643f6c1f2fcf8fdd6bdabf8f33b3f41fd511ac518cf6a316a6b3c8ce840"
MANIFEST_SHA = "b174b6f3185890b7a207884f2854f24374abd929aeeb79d65de890a34603f060"


def register() -> None:
    result = Path("knowledge/nodes/results/RESULT-H1-OOS-WUP-COMPLETE-V1.yaml")
    text = result.read_text(encoding="utf-8")
    if "performance_rows_sha256:" not in text:
        text = text.replace(
            "  scoring_rows: 66983\n",
            "  scoring_rows: 66983\n"
            f"  performance_rows_sha256: {PARQUET_SHA}\n"
            f"  canonical_summary_sha256: {SUMMARY_SHA}\n",
        )
    artifact = "    - results/h1_oos_pr_b/h1_oos_rows.parquet\n"
    if artifact not in text:
        text = text.replace(
            "    - results/h1_oos_pr_b/h1_oos_summary.csv\n",
            "    - results/h1_oos_pr_b/h1_oos_summary.csv\n" + artifact,
        )
    result.write_text(text, encoding="utf-8")

    doc = Path("docs/h1-oos-wup-pr-b-result-2026-09-07.md")
    doc.write_text(
        "# H1 WUP rolling-origin OOS result — PR B\n\n"
        "The preregistered aggregate country-balanced gate passes: relative RMSE improvement is "
        "10.62% (threshold ≥5%) and MAE difference is −0.002421 (threshold ≤0). The row-weighted "
        "aggregate also passes. H1 therefore derives to `evidence_supported`; no lifecycle field "
        "or gate threshold was manually edited.\n\n"
        "Per-origin reversals remain material: 2020 fails both RMSE and MAE under both weighting "
        "regimes, and 2000 fails RMSE under row weighting. The aggregate pass is not uniform across "
        "origins.\n\n"
        "Frozen panel identity: `a38203c78c42c95b27b2850d4c305eee077f132733f6eceb8f8d1d8e75cec9f2`. "
        "Performance builder commit: `e3505aad2f1e2682e3e88b3eb98af6140e59efc8`. Freeze construction "
        "commit: `88d407928e3a77f6975e0791741cd59ae7b08994`. Source SHA-256: "
        "`3a96030d87aec6c1c50f658d5321067d6345e1ab936c5d2854524f972caa75c0`.\n\n"
        f"Performance rows SHA-256: `{PARQUET_SHA}`. Canonical locked summary SHA-256: "
        f"`{SUMMARY_SHA}`. The previous committed summary differed only in two last-bit "
        "floating-point string renderings (about 10^-18); aggregate metrics, gates, and substantive "
        "per-origin conclusions were identical. The exact locked builder serialization is retained "
        "as canonical.\n\n"
        "Limitation: this is historical pseudo-OOS on harmonized WUP series. Passing this gate does "
        "not substitute for external validation against direct-count census observations.\n",
        encoding="utf-8",
    )

    packages_path = Path("results/durable_evidence_packages.csv")
    with packages_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        packages = list(reader)
    assert fields is not None
    packages = [row for row in packages if row["package_id"] != PACKAGE_ID]
    packages.append(
        {
            "package_id": PACKAGE_ID,
            "result_document": doc.as_posix(),
            "workflow_path": ".github/workflows/h1-wup-oos-pr-b.yml",
            "workflow_run_id": "34151316649",
            "artifact_id": "10029452326",
            "artifact_name": "wup-h1-oos-pr-b",
            "artifact_sha256": "d8104aebfbb78eaf45ff9cffc4f0f7f51fb72fc9e7fed12a0a10b52aeb645a59",
            "artifact_expires_at": "2026-12-06T18:22:15+00:00",
            "producing_commit": "d43c4e921d26013c50030af676e9be977838bf12",
            "generation_command": "uv run --locked python -m urban_growth.h1_oos build --f21 data/raw/WUP2025-F21-DEGURBA-Cities_Pop.xlsx --output-dir results/h1_oos_pr_b --commit e3505aad2f1e2682e3e88b3eb98af6140e59efc8",
            "parameters_json": json.dumps(
                {
                    "construction_commit": "e3505aad2f1e2682e3e88b3eb98af6140e59efc8",
                    "freeze_construction_commit": "88d407928e3a77f6975e0791741cd59ae7b08994",
                    "fence_stage": "pr_b_performance",
                    "frozen_panel_sha256": "a38203c78c42c95b27b2850d4c305eee077f132733f6eceb8f8d1d8e75cec9f2",
                    "summary_sha256": SUMMARY_SHA,
                },
                separators=(",", ":"),
            ),
            "source_ids_json": '["un_wup_2025_cities"]',
            "input_hash_manifest": "results/h1_oos_pr_b/input_sha256.txt",
            "input_hash_manifest_sha256": MANIFEST_SHA,
            "storage_class": "git_repository",
            "retention_policy": "retained_with_git_history",
            "evidence_owner": "danielastone",
            "expected_availability": "public_while_repository_retained",
            "restoration_procedure": "retrieve the registered F21 source from data/sources.json, verify the committed input hash manifest, and rerun the registered generation command",
            "rights_scope": "derived_parquet_committable_cc_by_3_0_igo",
            "notes": "PR B performance evidence; raw F21 bytes remain excluded; locked builder serialization is canonical; fence_stage=pr_b_performance",
        }
    )
    with packages_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(packages)

    outputs_path = Path("results/durable_evidence_outputs.csv")
    with outputs_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        outputs = list(reader)
    assert fields is not None
    outputs = [row for row in outputs if row["package_id"] != PACKAGE_ID]
    outputs.extend(
        [
            {
                "package_id": PACKAGE_ID,
                "artifact_member": "outputs/h1_oos_rows.parquet",
                "repository_path": "results/h1_oos_pr_b/h1_oos_rows.parquet",
                "sha256": PARQUET_SHA,
                "rows": "66983",
                "columns": "34",
                "media_type": "application/vnd.apache.parquet",
                "storage_status": "committed",
            },
            {
                "package_id": PACKAGE_ID,
                "artifact_member": "outputs/h1_oos_summary.csv",
                "repository_path": "results/h1_oos_pr_b/h1_oos_summary.csv",
                "sha256": SUMMARY_SHA,
                "rows": "18",
                "columns": "14",
                "media_type": "text/csv",
                "storage_status": "committed",
            },
        ]
    )
    with outputs_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(outputs)


if __name__ == "__main__":
    register()

"""Create a staged city-reliability evidence artifact from workflow inputs."""

from __future__ import annotations

import json
import os
from pathlib import Path

from urban_growth.city_reliability_intake import canonical_json, validate_intake


def main() -> None:
    payload = json.loads(os.environ["EVIDENCE_JSON"])
    record = validate_intake(
        payload,
        location_id=os.environ["LOCATION_ID"],
        location_label=os.environ["LOCATION_LABEL"],
        reference_date=os.environ["REFERENCE_DATE"],
        use_case_id=os.environ["USE_CASE_ID"],
        submitted_by=os.environ["SUBMITTED_BY"],
    )
    output_path = Path(os.environ.get("OUTPUT_PATH", "city-reliability-intake.json"))
    output_path.write_text(canonical_json(record), encoding="utf-8")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        lines = [
            "## City-level reliability evidence intake",
            "",
            f"- Location: `{record['location_id']}` — {record['location_label']}",
            f"- Reference date: `{record['reference_date']}`",
            f"- Use case: `{record['use_case_id']}`",
            "- Status: staged documentary evidence; analytical use is not authorized",
            "",
            "No score, tier, band, archetype, or cross-signal classification was produced.",
        ]
        with Path(summary_path).open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
EXE002 The file is executable but no shebang is present
--> scripts/capture_city_reliability_evidence.py:1:1

Found 1 error.
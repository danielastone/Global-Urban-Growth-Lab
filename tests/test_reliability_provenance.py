import csv
from dataclasses import replace

import pytest

from urban_growth.reliability_provenance import (
    DatasetSnapshot,
    TransformationRun,
    load_dataset_snapshots,
    load_transformation_runs,
    snapshot_from_manifest_record,
    snapshot_id_for,
    validate_dataset_snapshots,
    validate_evidence_lineage,
    validate_transformation_runs,
)
from urban_growth.sources import SourceCatalogError, load_catalog, load_licenses

HASH_A = "a" * 64
HASH_B = "b" * 64
COMMIT = "c" * 40


def _snapshot(*, sha256: str = HASH_A) -> DatasetSnapshot:
    return DatasetSnapshot(
        snapshot_id=snapshot_id_for("un_wpp_2024", sha256),
        source_id="un_wpp_2024",
        source_url="https://population.un.org/wpp/example.csv",
        retrieval_method="file_download",
        retrieved_at="2026-09-02T20:15:00Z",
        source_release="2024 Revision",
        source_observation_start="1950",
        source_observation_end="2023",
        local_path=f"data/raw/{sha256[:8]}.csv",
        sha256=sha256,
        media_type="text/csv",
        license_id="unresolved_exact_release",
        redistribution_status="not_committed",
        capture_notes="Synthetic test metadata; no source bytes included.",
    )


def _run(snapshot: DatasetSnapshot) -> TransformationRun:
    return TransformationRun.build(
        code_commit=COMMIT,
        entry_point="scripts/build_reliability.py",
        parameters={"dimension": "census", "strict": True},
        input_snapshot_ids=[snapshot.snapshot_id],
        started_at="2026-09-02T20:20:00Z",
        completed_at="2026-09-02T20:21:00Z",
        output_path="data/processed/reliability.csv",
        output_sha256=HASH_B,
    )


def _registries() -> tuple[dict, dict]:
    catalog = load_catalog("data/sources.json")
    return catalog, load_licenses("data/licenses.json", catalog=catalog)


def test_repository_provenance_registries_have_locked_headers() -> None:
    catalog, licenses = _registries()
    snapshots = load_dataset_snapshots("data/reliability_snapshots.csv")
    runs = load_transformation_runs("data/reliability_transformations.csv")
    assert len(snapshots) == 2
    assert snapshots[0].source_id == "unsd_census_dates_2026_02_03"
    assert snapshots[0].redistribution_status == "not_committed_pending_terms_review"
    assert snapshots[1].source_id == "unsd_m49_overview_2026_09_03"
    assert runs == []
    validate_dataset_snapshots(snapshots, catalog=catalog, licenses=licenses)
    validate_transformation_runs(runs, snapshots=snapshots)


def test_legacy_manifest_promotion_requires_explicit_capture_metadata() -> None:
    catalog, licenses = _registries()
    with open("data/manifest.csv", newline="", encoding="utf-8") as handle:
        record = next(csv.DictReader(handle))
    snapshot = snapshot_from_manifest_record(
        record,
        catalog=catalog,
        licenses=licenses,
        retrieval_method="file_download",
        retrieved_at="2026-08-27T14:30:00Z",
        media_type="application/zip",
        source_observation_start="1950",
        source_observation_end="2018",
        capture_notes="UTC timestamp recovered from acquisition log.",
    )
    assert snapshot.snapshot_id == f"{record['source_id']}:{record['sha256']}"
    assert snapshot.license_id == "CC-BY-3.0-IGO"
    validate_dataset_snapshots([snapshot], catalog=catalog, licenses=licenses)


def test_date_only_retrieval_does_not_fake_timestamp_precision() -> None:
    catalog, licenses = _registries()
    with pytest.raises(SourceCatalogError, match="UTC timestamp"):
        validate_dataset_snapshots(
            [replace(_snapshot(), retrieved_at="2026-09-02")],
            catalog=catalog,
            licenses=licenses,
        )


def test_snapshot_requires_observation_period_and_manual_evidence_notes() -> None:
    catalog, licenses = _registries()
    with pytest.raises(SourceCatalogError, match="source_observation_start"):
        validate_dataset_snapshots(
            [replace(_snapshot(), source_observation_start="")],
            catalog=catalog,
            licenses=licenses,
        )
    with pytest.raises(SourceCatalogError, match="cannot precede"):
        validate_dataset_snapshots(
            [
                replace(
                    _snapshot(),
                    source_observation_start="2024",
                    source_observation_end="2023",
                )
            ],
            catalog=catalog,
            licenses=licenses,
        )
    with pytest.raises(SourceCatalogError, match="require capture_notes"):
        validate_dataset_snapshots(
            [replace(_snapshot(), retrieval_method="manual_evidence", capture_notes="")],
            catalog=catalog,
            licenses=licenses,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("snapshot_id", "invented", "captured bytes"),
        ("source_url", "http://example.com/data.csv", "HTTPS"),
        ("retrieval_method", "live_api", "retrieval_method"),
        ("local_path", "../outside.csv", "relative project path"),
        ("license_id", "invented-license", "licenses.json"),
        ("source_release", "2026 Revision", "sources.json"),
    ],
)
def test_snapshot_validation_fails_closed(field: str, value: str, message: str) -> None:
    catalog, licenses = _registries()
    with pytest.raises(SourceCatalogError, match=message):
        validate_dataset_snapshots(
            [replace(_snapshot(), **{field: value})],
            catalog=catalog,
            licenses=licenses,
        )


def test_revised_captures_coexist_without_overwriting_prior_bytes() -> None:
    catalog, licenses = _registries()
    snapshots = [_snapshot(sha256=HASH_A), _snapshot(sha256=HASH_B)]
    validate_dataset_snapshots(snapshots, catalog=catalog, licenses=licenses)
    assert len({row.snapshot_id for row in snapshots}) == 2
    with pytest.raises(SourceCatalogError, match="Duplicate snapshot_id"):
        validate_dataset_snapshots([snapshots[0], snapshots[0]], catalog=catalog, licenses=licenses)


def test_transformation_identity_is_deterministic_and_validated() -> None:
    snapshot = _snapshot()
    first = _run(snapshot)
    second = _run(snapshot)
    assert first.transformation_run_id == second.transformation_run_id
    assert first.parameters_json == '{"dimension":"census","strict":true}'
    validate_transformation_runs([first], snapshots=[snapshot])


def test_transformation_rejects_unknown_input_and_noncanonical_parameters() -> None:
    snapshot = _snapshot()
    run = _run(snapshot)
    with pytest.raises(SourceCatalogError, match="Unknown input snapshot"):
        validate_transformation_runs(
            [replace(run, input_snapshot_ids='["missing"]')], snapshots=[snapshot]
        )
    with pytest.raises(SourceCatalogError, match="canonical JSON object"):
        validate_transformation_runs(
            [replace(run, parameters_json='{"strict": true, "dimension": "census"}')],
            snapshots=[snapshot],
        )


def test_transformation_rejects_bad_commit_and_reverse_chronology() -> None:
    snapshot = _snapshot()
    run = _run(snapshot)
    with pytest.raises(SourceCatalogError, match="full lowercase Git SHA"):
        validate_transformation_runs([replace(run, code_commit="abc")], snapshots=[snapshot])
    with pytest.raises(SourceCatalogError, match="cannot precede"):
        validate_transformation_runs(
            [replace(run, completed_at="2026-09-02T20:19:00Z")], snapshots=[snapshot]
        )


def test_evidence_rows_require_connected_snapshot_and_transformation() -> None:
    snapshot = _snapshot()
    run = _run(snapshot)
    evidence = {
        "country_id": "USA",
        "source_id": snapshot.source_id,
        "source_release": snapshot.source_release,
        "snapshot_id": snapshot.snapshot_id,
        "transformation_run_id": run.transformation_run_id,
    }
    validate_evidence_lineage([evidence], snapshots=[snapshot], runs=[run])
    with pytest.raises(SourceCatalogError, match="no registered snapshot"):
        validate_evidence_lineage(
            [{**evidence, "snapshot_id": "missing"}], snapshots=[snapshot], runs=[run]
        )
    with pytest.raises(SourceCatalogError, match="no registered transformation"):
        validate_evidence_lineage(
            [{**evidence, "transformation_run_id": "missing"}],
            snapshots=[snapshot],
            runs=[run],
        )


def test_evidence_snapshot_must_be_an_input_to_declared_transformation() -> None:
    snapshot = _snapshot(sha256=HASH_A)
    other = _snapshot(sha256=HASH_B)
    run = _run(other)
    with pytest.raises(SourceCatalogError, match="not an input"):
        validate_evidence_lineage(
            [
                {
                    "snapshot_id": snapshot.snapshot_id,
                    "transformation_run_id": run.transformation_run_id,
                }
            ],
            snapshots=[snapshot, other],
            runs=[run],
        )

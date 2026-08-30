"""Source catalog validation and immutable-file inventory utilities."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

CATALOG_REQUIRED = {
    "source_id",
    "priority",
    "status",
    "publisher",
    "dataset",
    "release",
    "landing_page",
    "documentation_url",
    "retrieval",
    "formats",
    "coverage",
    "unit",
    "role",
    "upstream_dependencies",
    "redistribution",
    "citation",
    "notes",
}

LICENSE_USE_FIELDS = {
    "internal_research_use",
    "internal_commercial_use",
    "raw_redistribution",
    "derived_data_distribution",
    "model_training_or_fitting",
    "customer_output_use",
}

LICENSE_REQUIRED = {
    "source_id",
    "license_id",
    "license_url",
    "licensor",
    "rights_holder",
    *LICENSE_USE_FIELDS,
    "attribution_required",
    "attribution_spec",
    "share_alike",
    "license_election",
    "copyright_coverage",
    "sui_generis_database_rights_coverage",
    "database_maker_eligibility",
    "applicable_law",
    "dispute_forum_or_mechanism",
    "sovereign_or_igo_immunity",
    "approval_reference",
    "terms_snapshot_hash",
    "notes",
}

MANIFEST_FIELDS = [
    "source_id", "publisher", "dataset", "release", "retrieved_at", "source_url",
    "license", "local_path", "sha256", "redistribution_allowed", "notes",
]


class SourceCatalogError(ValueError):
    """Raised when source metadata is incomplete or internally inconsistent."""


@dataclass(frozen=True)
class InventoryRecord:
    source_id: str
    publisher: str
    dataset: str
    release: str
    retrieved_at: str
    source_url: str
    license: str
    local_path: str
    sha256: str
    redistribution_allowed: str
    notes: str

    def as_dict(self) -> dict[str, str]:
        return {field: str(getattr(self, field)) for field in MANIFEST_FIELDS}


def load_catalog(path: str | Path = "data/sources.json") -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        catalog = json.load(handle)
    validate_catalog(catalog)
    return catalog


def load_licenses(
    path: str | Path = "data/licenses.json", *, catalog: dict | None = None
) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        registry = json.load(handle)
    validate_licenses(registry, catalog=catalog)
    return registry


def default_catalog_path() -> Path:
    """Locate the project catalog from the working tree or an editable install."""
    candidates = [Path.cwd(), *Path.cwd().parents, Path(__file__).resolve().parents[2]]
    for root in candidates:
        candidate = root / "data" / "sources.json"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Cannot locate data/sources.json; pass --catalog with the project catalog path"
    )


def validate_catalog(catalog: dict) -> None:
    if catalog.get("schema_version") != 1:
        raise SourceCatalogError("Unsupported or missing catalog schema_version")
    sources = catalog.get("sources")
    if not isinstance(sources, list) or not sources:
        raise SourceCatalogError("Catalog must contain a non-empty sources list")
    ids: list[str] = []
    for index, source in enumerate(sources):
        missing = sorted(CATALOG_REQUIRED.difference(source))
        if missing:
            raise SourceCatalogError(f"Source {index} missing fields: {', '.join(missing)}")
        ids.append(source["source_id"])
        for field in ("landing_page", "documentation_url"):
            parsed = urlparse(source[field])
            if parsed.scheme != "https" or not parsed.netloc:
                raise SourceCatalogError(f"{source['source_id']} has invalid {field}")
        if not source["formats"]:
            raise SourceCatalogError(f"{source['source_id']} has no declared formats")
        dependencies = source["upstream_dependencies"]
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) and item for item in dependencies
        ):
            raise SourceCatalogError(
                f"{source['source_id']} upstream_dependencies must be a list of strings"
            )
    duplicates = sorted({source_id for source_id in ids if ids.count(source_id) > 1})
    if duplicates:
        raise SourceCatalogError(f"Duplicate source_id values: {', '.join(duplicates)}")
    known = set(ids)
    dangling = sorted(
        {
            dependency
            for source in sources
            for dependency in source["upstream_dependencies"]
            if dependency not in known
        }
    )
    if dangling:
        raise SourceCatalogError(f"Unknown upstream dependencies: {', '.join(dangling)}")


def validate_licenses(registry: dict, *, catalog: dict | None = None) -> None:
    if registry.get("schema_version") != 1:
        raise SourceCatalogError("Unsupported or missing license schema_version")
    if registry.get("default_policy") != "deny":
        raise SourceCatalogError("License registry default_policy must be deny")
    allowed = set(registry.get("allowed_use_values", []))
    required_allowed = {
        "permitted", "prohibited", "permission_required", "legal_review_required", "unresolved"
    }
    if allowed != required_allowed:
        raise SourceCatalogError("License registry has invalid allowed_use_values")
    records = registry.get("sources")
    if not isinstance(records, list) or not records:
        raise SourceCatalogError("License registry must contain source records")
    ids: list[str] = []
    for index, record in enumerate(records):
        missing = sorted(LICENSE_REQUIRED.difference(record))
        if missing:
            raise SourceCatalogError(
                f"License source {index} missing fields: {', '.join(missing)}"
            )
        source_id = record["source_id"]
        ids.append(source_id)
        parsed = urlparse(record["license_url"])
        if parsed.scheme != "https" or not parsed.netloc:
            raise SourceCatalogError(f"{source_id} has invalid license_url")
        invalid = sorted(
            field for field in LICENSE_USE_FIELDS if record[field] not in allowed
        )
        if invalid:
            raise SourceCatalogError(
                f"{source_id} has invalid license decisions: {', '.join(invalid)}"
            )
        if record["attribution_required"] and not record["attribution_spec"].strip():
            raise SourceCatalogError(f"{source_id} requires an attribution specification")
    duplicates = sorted({source_id for source_id in ids if ids.count(source_id) > 1})
    if duplicates:
        raise SourceCatalogError(f"Duplicate license source_id values: {', '.join(duplicates)}")
    if catalog is not None:
        catalog_ids = {source["source_id"] for source in catalog["sources"]}
        registry_ids = set(ids)
        if catalog_ids != registry_ids:
            missing = sorted(catalog_ids - registry_ids)
            extra = sorted(registry_ids - catalog_ids)
            raise SourceCatalogError(
                f"License registry/catalog mismatch; missing={missing}, extra={extra}"
            )


def license_by_source_id(registry: dict, source_id: str) -> dict:
    matches = [record for record in registry["sources"] if record["source_id"] == source_id]
    if not matches:
        raise SourceCatalogError(f"No license decision for source_id: {source_id}")
    return matches[0]


def require_permitted_use(registry: dict, source_id: str, use: str) -> dict:
    if use not in LICENSE_USE_FIELDS:
        raise SourceCatalogError(f"Unknown licensed use: {use}")
    record = license_by_source_id(registry, source_id)
    decision = record[use]
    if decision != "permitted":
        raise SourceCatalogError(
            f"DENIED: {source_id} {use} is {decision}; fail-closed policy requires permitted"
        )
    return record


def source_by_id(catalog: dict, source_id: str) -> dict:
    matches = [source for source in catalog["sources"] if source["source_id"] == source_id]
    if not matches:
        raise SourceCatalogError(f"Unknown source_id: {source_id}")
    return matches[0]


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory_file(
    file_path: str | Path,
    source: dict,
    *,
    source_url: str,
    retrieved_at: str | None = None,
    license_text: str = "review_required",
    redistribution_allowed: str = "unknown",
    notes: str = "",
) -> InventoryRecord:
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if urlparse(source_url).scheme != "https":
        raise SourceCatalogError("source_url must be an exact HTTPS retrieval URL")
    return InventoryRecord(
        source_id=source["source_id"], publisher=source["publisher"],
        dataset=source["dataset"], release=source["release"],
        retrieved_at=retrieved_at or datetime.now(UTC).date().isoformat(), source_url=source_url,
        license=license_text, local_path=path.as_posix(), sha256=sha256_file(path),
        redistribution_allowed=redistribution_allowed, notes=notes,
    )


def append_manifest(record: InventoryRecord, path: str | Path = "data/manifest.csv") -> None:
    manifest = Path(path)
    existing: list[dict[str, str]] = []
    if manifest.exists() and manifest.stat().st_size:
        with manifest.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != MANIFEST_FIELDS:
                raise SourceCatalogError("Manifest header does not match the required schema")
            existing = list(reader)
    if any(row["sha256"] == record.sha256 for row in existing):
        raise SourceCatalogError("This exact file checksum is already registered")
    with manifest.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        if not existing and manifest.stat().st_size == 0:
            writer.writeheader()
        writer.writerow(record.as_dict())


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect and inventory urban-growth sources")
    parser.add_argument("--catalog")
    parser.add_argument("--licenses")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list")
    subparsers.add_parser("verify-catalog")
    subparsers.add_parser("verify-licenses")
    license_check = subparsers.add_parser("check-license")
    license_check.add_argument("--source-id", required=True)
    license_check.add_argument("--use", required=True, choices=sorted(LICENSE_USE_FIELDS))
    inventory = subparsers.add_parser("inventory")
    inventory.add_argument("file")
    inventory.add_argument("--source-id", required=True)
    inventory.add_argument("--source-url", required=True)
    inventory.add_argument("--manifest", default="data/manifest.csv")
    args = parser.parse_args()
    catalog = load_catalog(args.catalog or default_catalog_path())
    license_path = args.licenses or default_catalog_path().with_name("licenses.json")
    if args.command == "list":
        for source in sorted(catalog["sources"], key=lambda item: item["priority"]):
            print(f"{source['priority']}\t{source['source_id']}\t{source['status']}\t{source['dataset']}")
    elif args.command == "verify-catalog":
        print(f"valid: {len(catalog['sources'])} sources")
    elif args.command == "verify-licenses":
        registry = load_licenses(license_path, catalog=catalog)
        print(f"valid: {len(registry['sources'])} license decisions; default=deny")
    elif args.command == "check-license":
        registry = load_licenses(license_path, catalog=catalog)
        try:
            record = require_permitted_use(registry, args.source_id, args.use)
        except SourceCatalogError as error:
            raise SystemExit(str(error)) from error
        print(f"permitted: {record['source_id']} {args.use} under {record['license_id']}")
    else:
        source = source_by_id(catalog, args.source_id)
        record = inventory_file(args.file, source, source_url=args.source_url)
        append_manifest(record, args.manifest)
        print(record.sha256)


if __name__ == "__main__":
    main()

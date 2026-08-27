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
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list")
    subparsers.add_parser("verify-catalog")
    inventory = subparsers.add_parser("inventory")
    inventory.add_argument("file")
    inventory.add_argument("--source-id", required=True)
    inventory.add_argument("--source-url", required=True)
    inventory.add_argument("--manifest", default="data/manifest.csv")
    args = parser.parse_args()
    catalog = load_catalog(args.catalog or default_catalog_path())
    if args.command == "list":
        for source in sorted(catalog["sources"], key=lambda item: item["priority"]):
            print(f"{source['priority']}\t{source['source_id']}\t{source['status']}\t{source['dataset']}")
    elif args.command == "verify-catalog":
        print(f"valid: {len(catalog['sources'])} sources")
    else:
        source = source_by_id(catalog, args.source_id)
        record = inventory_file(args.file, source, source_url=args.source_url)
        append_manifest(record, args.manifest)
        print(record.sha256)


if __name__ == "__main__":
    main()

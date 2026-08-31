"""Acquisition preflight for the Mexico multiwave locality panel."""

from __future__ import annotations

import re

import pandas as pd

from urban_growth.io import SourceSchemaError, require_columns

REQUIRED_POPULATION_YEARS = (1990, 1995, 2000, 2005, 2010, 2020)
REQUIRED_SUPPORT_ROLES = {
    "official_relationships",
    "locality_history",
}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def validate_mexico_acquisition_registry(registry: pd.DataFrame) -> pd.DataFrame:
    """Validate source registration before any Mexico concordance run.

    Registration is intentionally stricter than source discovery. A landing page is not
    an acquired input: each row must identify an exact local file/export, retrieval date,
    exact source URL or reproducible service query, checksum, license review status, and
    an explicit completeness assertion.
    """
    required = {
        "role",
        "event_year",
        "event_type",
        "publisher",
        "dataset",
        "retrieved_at",
        "source_url",
        "local_path",
        "sha256",
        "license_reviewed",
        "completeness_verified",
        "national_record_cap_avoided",
        "status",
    }
    require_columns(registry, required, source_name="Mexico acquisition registry")
    out = registry.copy()

    duplicate_key = ["role", "event_year", "local_path"]
    if out.duplicated(duplicate_key).any():
        raise SourceSchemaError("Mexico acquisition registry has duplicate source rows")

    complete = out["status"].eq("acquired")
    for column in ("publisher", "dataset", "retrieved_at", "source_url", "local_path"):
        if out.loc[complete, column].fillna("").astype(str).str.strip().eq("").any():
            raise SourceSchemaError(f"Acquired Mexico rows require {column}")

    hashes = out.loc[complete, "sha256"].fillna("").astype(str).str.lower()
    if (~hashes.map(lambda value: bool(SHA256_PATTERN.fullmatch(value)))).any():
        raise SourceSchemaError("Acquired Mexico rows require lowercase SHA-256 checksums")

    for column in ("license_reviewed", "completeness_verified", "national_record_cap_avoided"):
        if not pd.api.types.is_bool_dtype(out[column].dtype):
            raise SourceSchemaError(f"{column} must be boolean")
        if (~out.loc[complete, column]).any():
            raise SourceSchemaError(f"Acquired Mexico rows must pass {column}")

    population = out.loc[out["role"].eq("population")]
    acquired_population_years = set(population.loc[population["status"].eq("acquired"), "event_year"])
    missing_population_years = sorted(set(REQUIRED_POPULATION_YEARS) - acquired_population_years)

    acquired_roles = set(out.loc[out["status"].eq("acquired"), "role"])
    missing_support_roles = sorted(REQUIRED_SUPPORT_ROLES - acquired_roles)

    geometry = out.loc[out["role"].eq("vintage_geometry") & out["status"].eq("acquired")]
    acquired_geometry_years = set(geometry["event_year"])
    missing_geometry_years = sorted(set(REQUIRED_POPULATION_YEARS) - acquired_geometry_years)

    ready = not missing_population_years and not missing_support_roles and not missing_geometry_years
    out.attrs["mexico_acquisition_ready"] = ready
    out.attrs["missing_population_years"] = missing_population_years
    out.attrs["missing_geometry_years"] = missing_geometry_years
    out.attrs["missing_support_roles"] = missing_support_roles
    return out


def require_mexico_acquisition_ready(registry: pd.DataFrame) -> pd.DataFrame:
    """Fail closed until all population and geography waves are actually registered."""
    checked = validate_mexico_acquisition_registry(registry)
    if not checked.attrs["mexico_acquisition_ready"]:
        raise SourceSchemaError(
            "Mexico acquisition is incomplete: "
            f"population years={checked.attrs['missing_population_years']}; "
            f"geometry years={checked.attrs['missing_geometry_years']}; "
            f"support roles={checked.attrs['missing_support_roles']}"
        )
    return checked

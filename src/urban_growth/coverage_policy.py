"""Repository-controlled registry for headline outcome-coverage policies."""

from __future__ import annotations

from dataclasses import dataclass

from urban_growth.io import SourceSchemaError


@dataclass(frozen=True)
class HeadlineCoveragePolicy:
    """A versioned minimum observed-outcome coverage rule."""

    policy_id: str
    minimum_observed_outcome_share: float
    reference: str


# Deliberately empty until the project adopts a substantive threshold.
# Adding or changing a policy requires a reviewed repository commit/PR.
REGISTERED_HEADLINE_COVERAGE_POLICIES: tuple[HeadlineCoveragePolicy, ...] = ()


def resolve_registered_coverage_policy(policy_id: str) -> HeadlineCoveragePolicy:
    """Resolve one repository-registered coverage policy by stable ID."""
    requested = str(policy_id).strip()
    if not requested:
        raise SourceSchemaError("coverage_policy_id must name a repository-registered policy")

    matches = [policy for policy in REGISTERED_HEADLINE_COVERAGE_POLICIES if policy.policy_id == requested]
    if not matches:
        raise SourceSchemaError(
            f"Unknown coverage_policy_id {requested!r}; add the policy to the versioned registry before headline use"
        )
    if len(matches) != 1:
        raise SourceSchemaError(f"Duplicate registered coverage policy ID: {requested}")

    policy = matches[0]
    minimum = float(policy.minimum_observed_outcome_share)
    if not 0 < minimum <= 1:
        raise SourceSchemaError(
            f"Registered coverage policy {requested!r} has an invalid minimum observed-outcome share"
        )
    if not str(policy.reference).strip():
        raise SourceSchemaError(f"Registered coverage policy {requested!r} lacks a policy reference")
    return policy

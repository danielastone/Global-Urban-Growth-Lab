# City-level reliability evidence intake

This manual workflow captures **staged documentary assertions**. It is not a classifier.
It never emits a score, tier, band, archetype, or city-fitness decision. The five signals
are retained separately and do not override the City Data Fitness Standard or the
country-level reliability matrix.

Each non-unknown assertion requires `value`, `source_id`, `snapshot_id`,
`source_release`, `observation_date`, and `citation`. The workflow validates structure but
does not pretend that a typed snapshot identifier is registered. Its JSON artifact is
therefore marked `analytical_use_authorized: false`. Promotion requires snapshot-registry
verification, a registered transformation, and a separate use-specific fitness decision.

Unknown evidence uses `value: "unknown"` and a substantive `notes` explanation. It must
not contain placeholder provenance. In particular, `no_issue_documented` and
`no_documented_incentive` mean that a cited source makes that bounded documentary claim;
they are not synonyms for missing evidence and receive no favorable numerical treatment.

## Payload shape

```json
{
  "verification": {
    "value": "place_direct",
    "source_id": "registered_source_id",
    "snapshot_id": "candidate_snapshot_id",
    "source_release": "named release",
    "observation_date": "2025-01-01",
    "citation": "page, table, or record locator"
  },
  "incentive": {"value": "unknown", "notes": "No reviewed evidence yet."},
  "aggregate_check": {"value": "unknown", "notes": "No reviewed evidence yet."},
  "conduit": {"value": "unknown", "notes": "No reviewed evidence yet."},
  "granular_treatment": {"value": "unknown", "notes": "No reviewed evidence yet."}
}
```

Allowed values:

| Signal | Values |
|---|---|
| `verification` | `none_documented`, `country_level_only`, `place_direct`, `unknown` |
| `incentive` | `aligned_distortion_risk`, `heterogeneous_incentives`, `no_documented_incentive`, `unknown` |
| `aggregate_check` | `none_documented`, `partial`, `strong`, `unknown` |
| `conduit` | `obscured`, `ordinary`, `heightened_scrutiny`, `unknown` |
| `granular_treatment` | `suspected_undisclosed`, `disclosed_bounded`, `no_issue_documented`, `unknown` |

The word `strong` is source-specific documentary text, not a universal reliability rank.

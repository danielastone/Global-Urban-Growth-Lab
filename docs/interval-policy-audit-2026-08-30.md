# Pass 3 audit — sequential interval policy and sparse cells

Date: 30 August 2026

## Verdicts

### Q1 — sequential leakage: PASS

`sequential_interval_calibration` constructs each calibration set with
`origin < test origin`. A recent-window policy then truncates that already eligible
set to its latest three origins. Both production scripts call only
`registered_sequential_interval_calibration` with literal policy identifiers. There
is no script pre-pass that pools future residuals to choose a policy, parameter or
reported stratum.

This pass applies to the mechanics of each reported row. It does not establish that
the policy menu itself was selected prospectively.

### Q2 — policy-selection timing: UNRESOLVED-PROCESS

Git history establishes the following sequence:

1. Sequential calibration implementation: `8c4e2fa6fb1e48b530cc85089f74452a6872f013`.
2. Base policy registry: `2e9d7784dfd623877a4ef6d9b25b515918f3fcf7`.
3. Recent-three-origin policies: `bd2be2e5aaf5e809bfbcddaed0c38b9826650cac`.
4. Equal-country policies: `5fd82b646cdb46c70369184dfab757b81b9592ac`.
5. Locked specification: `9f1c8cb76da4655493e16797eacb7f96c268e61c`.

The source tree cannot establish when the first real-data calibration output was
computed because generated outputs were not committed. No earlier timestamped design
artifact names all six policies and their exact parameters. The repository therefore
has no basis for `stratification_prespecified=True` or for a prospective-registration
claim.

Resolution would require a timestamped external artifact predating the first real
run, containing the exact six identifiers and values for miscoverage, minimum rows,
minimum origins, recent-window length, weighting and grouping. Without that evidence,
the policies remain retrospective sensitivity analyses.

### Q3 — sparse-cell handling: FAIL, remediated

Before this change, cells below `minimum_calibration_rows` or
`minimum_calibration_origins` hit `continue` and vanished. The output therefore
contained only eligible cells and could not disclose the share or identity of
candidate cells omitted for sparse calibration history.

Registered runs now retain every origin/model/stratum candidate with:

- `calibration_eligible`;
- `calibration_exclusion_reason`;
- available row, origin and country counts;
- policy timing and lock-commit metadata.

Ineligible rows carry no realized coverage statistic. Coverage summaries must report
their eligibility denominator separately; they may not silently drop these rows.

The registered production rerun gives the following eligibility audit:

| Source and table | Candidate cells | Eligible | Ineligible | Eligible share |
|---|---:|---:|---:|---:|
| WUP overall | 288 | 216 | 72 | 75% |
| WUP by size | 1,728 | 1,296 | 432 | 75% |
| GHSL fixed overall | 120 | 90 | 30 | 75% |
| GHSL fixed by size | 840 | 630 | 210 | 75% |

All ineligible cells occur before enough prior origins are available. Some also fail
the 100-row minimum. They are calibration-availability exclusions, not empirical
coverage failures.

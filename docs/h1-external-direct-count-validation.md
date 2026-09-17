# H1 external direct-count validation protocol

This document is the methodology baseline for external validation of H1 after the WUP pseudo-OOS result. It is intentionally outcome-free. No country-level forecast performance may be added until the relevant PR-A diagnostics and sample identity are accepted.

## Why this is a separate validation layer

The merged WUP result uses a harmonized historical series. External validation must use direct-count census observations that are not silently routed through the WUP harmonization process, must make boundary comparability auditable, and must preserve the predictive rather than causal interpretation of H1.

## Primary validation pair and sequencing

Mexico is the first construction pilot and first planned direct-count external test. The United States is the second primary geography and provides a structurally distinct high-income, suburban/polycentric validation environment. India is retained as a later 2001–2011 robustness test; the next Indian census is prospectively scheduled for 2027, so one completed modern interval does not support the full rolling design. Brazil, Japan, and China require separate protocol adaptations before use as primary validation geographies.

## 10-year estimand

Mexico and U.S. primary tests use direct census rounds at a 10-year horizon. The annualized log growth estimand is:

`g = (ln(P_target) - ln(P_origin)) / 10`

No interpolation is permitted to manufacture 5-year direct-count observations for the primary test. A 10-year annualized growth rate has lower variance than the 5-year WUP estimand, so error magnitudes are not directly interchangeable even though the numerical acceptance thresholds are deliberately retained.

## Acceptance gate

`GATE-H1-DIRECT-COUNT-10Y-OOS` is horizon-scoped with `horizon_years: 10` and preserves the preregistered numerical conditions:

- relative RMSE improvement >= 5%;
- MAE difference <= 0;
- failure interpretation: `falsifies_primary_claim`.

A 5-year external test must use a different gate node.

## Peer signal and sample adequacy

The primary comparator retains the WUP estimand structure: country-wide leave-city-out peer growth. State/subnational peer models are sensitivity analyses, not substitutions for the primary signal.

The WUP >=30-country training gate is inapplicable to a single-country panel. External sample adequacy instead uses minimum eligible scoring cities, minimum leave-city-out peer count, and minimum historical transitions. Exact thresholds are frozen after PR-A count diagnostics are visible but before any forecast performance is computed or exposed.

## Mexico PR A

Primary rounds are INEGI 2000, 2010, and 2020 direct census counts. The 2015 Encuesta Intercensal is excluded from primary evidence because it is a probabilistic sample estimate; it may be evaluated later as a mixed-source sensitivity after a separate comparability assessment.

The 2020 census measurement context is part of the primary evidence record whenever that round is used: the reference date is March 15, 2020. This context must appear in the panel metadata and later result limitation.

Before PR B, Mexico PR A must freeze:

- WUP source-basis/independence assessment;
- locality identity and concordance rules across 2000/2010/2020;
- explicit treatment of code changes, splits, mergers, reclassification, annexation/incorporation, and material boundary changes;
- row-level exclusion reasons and any area-change threshold;
- eligibility counts, peer-count distribution, historical-transition counts, and 50k–250k origin coverage;
- blind sample-adequacy thresholds;
- deterministic scoring-row identity and hash.

No silent population or boundary harmonization is permitted.

## Diagnostics-before-performance fence

PR A may contain source/provenance checks, WUP independence evidence, concordance, boundary exclusions, eligibility diagnostics, adequacy thresholds, and a frozen sample hash. It may not contain B0/B1 prediction errors, RMSE, MAE, relative improvement, gate decisions, or winner fields.

PR B can evaluate performance only against the accepted PR-A sample identity. Changing eligibility, concordance, horizon, peer signal, or adequacy thresholds requires a new PR-A version before rerunning performance.

## Lifecycle semantics

An external-validation test may be registered while pending without erasing H1's existing `evidence_supported` state. `externally_validated` becomes reachable only when a required external-validation test has a completed gate pass whose result is typed `validation_type: direct_count_external` and references a valid geography node. The external validation scope is derived from those passing result geographies; it is not manually asserted on H1.

A direct-count external result without geography is invalid by schema. Generated research status displays the derived scope once it exists.

## Column naming

Shared external panels use `origin_year` and `target_year`. The merged WUP package uses `period_start` and `period_end`; that is retained as a documented legacy naming inconsistency and does not reopen or invalidate the WUP evidence package.

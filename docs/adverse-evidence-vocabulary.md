# Adverse evidence controlled vocabulary

Fields that assert a potentially disqualifying condition — currently `administrative_reclassification`, `methodology_change`, and `known_inconsistency` — are evaluated as tri-state evidence.

Accepted evidence of presence is limited to explicit values such as boolean `true`, `1`, `true`, `yes`, `y`, `passed`, `valid`, or `present`. Accepted evidence of absence is limited to boolean `false`, `0`, `false`, `no`, `n`, `clear`, `none`, or `absent`.

Blank, missing, explicitly uncertain values, and any unrecognized string are treated as `unknown`. They do not count as evidence that the adverse condition is absent. This rule is intentionally fail-closed because source adapters and manually curated registries can otherwise introduce silent eligibility errors through typos or novel labels.

The City Data Fitness evaluator therefore distinguishes confirmed absence from unavailable or malformed evidence rather than coercing arbitrary strings to false.
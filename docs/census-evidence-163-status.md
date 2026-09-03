# Census evidence #163 — schema implemented, acquisition open

The executable census-event and estimate-incorporation contracts are implemented in
`src/urban_growth/census_evidence.py`. They enforce controlled vocabularies, chronology,
source-specific event identities, assertion uniqueness, explicit unknown states, and
estimate-series/vintage-qualified incorporation claims. Conflicting source assertions remain
separate rows. Census recency never implies quality, PES status, undercount, adjustment, or
incorporation.

Issue #163 is not empirically complete. UNSD publishes a maintained global census-date table,
but the required PES, undercount, coverage-adjustment, results-status, and WPP/IDB incorporation
evidence is distributed across country reports and publisher notes. Those artifacts still need
release-specific capture, checksums, licenses, crosswalks, and transformation lineage. A global
census-date scrape alone would satisfy only one field and must not be presented as completion.

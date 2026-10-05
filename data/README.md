# Data

No analytical data have been committed yet.

## Intended source classes

- United Nations World Urbanization Prospects city or urban-agglomeration estimates
- DEGURBA-related city, town, and rural classifications where redistribution is permitted
- National population and urban-share series
- Geographic coordinates, country boundaries, and accessibility measures
- Documented auxiliary sources used for case validation

## Rules

- Preserve raw downloads unchanged.
- Record source URL, release, retrieval date, license, checksum, and citation.
- Do not commit data when redistribution terms are unclear.
- Assign stable project identifiers; do not rely on names alone.
- Document boundary, definition, and name changes.
- Separate reported observations from interpolated or modeled estimates.
- Generate processed data only through code.
- Pass the intended operation through `urban-growth-sources check-license` before
  commercial ingestion, redistribution, model fitting, or customer delivery.

## Required manifest fields

```text
source_id
publisher
dataset
release
retrieved_at
source_url
license
local_path
sha256
redistribution_allowed
notes
```

The manifest records acquired files. It does not grant permission. Source-level legal
decisions and attribution requirements are maintained separately in
`data/licenses.json`; see [THIRD_PARTY_DATA.md](../THIRD_PARTY_DATA.md).

## Population-reliability provenance

`reliability_snapshots.csv` and `reliability_transformations.csv` extend the existing
source, license, and file-manifest registries for the population-data reliability matrix.
They are deliberately header-only until an open input is actually captured and a
transformation is executed.

- A snapshot identifies exact captured bytes using `source_id` plus SHA-256 and carries an
  ISO-8601 UTC retrieval timestamp and an explicit observation period. It does not replace
  `manifest.csv` or licensing review.
- A transformation identifies its full Git commit, canonical parameters, exact input
  snapshots, output hash, and UTC execution interval.
- An evidence row fails validation unless its declared snapshot is an input to its declared
  transformation.

Legacy `manifest.csv` rows contain only retrieval dates. They may be promoted into the new
snapshot registry only when the missing capture timestamp, observation period, and media
metadata can be supplied from evidence; the implementation does not invent midnight
timestamps.

Validate the committed registries with:

```bash
uv run --locked --extra dev urban-growth-sources verify-reliability-provenance
```

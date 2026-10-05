# Durable empirical-result evidence

GitHub Actions artifacts are transient execution conveniences. Their run IDs, artifact
IDs, archive digests, and expiry dates remain recorded for audit, but no retained claim
depends on downloading an Actions artifact after its retention window.

The durable contract consists of:

- results/durable_evidence_packages.csv: one row per cited empirical run, binding the
  result document to its workflow, producing commit, exact command and parameters, source
  identities, input-hash manifest, archive digest, rights scope, retention policy, and
  restoration procedure;
- results/durable_evidence_outputs.csv: one row per recovered or already committed
  scientific output, with its original artifact-member path, repository path, SHA-256,
  dimensions, media type, and storage state; and
- the permitted derived CSVs at the registered repository paths.

Raw WUP and GHSL files remain outside Git. Their exact hashes are retained in the input
manifests, and empirical workflows verify those registered hashes before analysis. The
committed result CSVs are derived evidence and remain subject to the attribution and
source-use terms documented in THIRD_PARTY_DATA.md and data/licenses.json.

Run the durable check with:

    uv run --locked python scripts/verify_durable_evidence.py

The validator fails for missing or changed outputs, changed input-hash manifests,
unregistered result documents that cite transient artifacts, malformed run provenance,
non-durable retention policies, and transient restoration URLs.

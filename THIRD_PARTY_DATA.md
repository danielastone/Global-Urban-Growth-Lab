# Third-party data rights

Apache-2.0 applies to this repository's software only. It does not license, relicense,
or change the terms of any dataset that the software reads. Catalog inclusion,
manifest registration, and workflow compatibility are metadata statements—not
permission to use or redistribute a source.

`data/licenses.json` is the machine-readable rights registry. It records separate
decisions for research use, commercial use, raw redistribution, derived-data
distribution, model fitting, and customer outputs. Its policy is **deny by default**:
only the literal value `permitted` passes an automated license check. `unresolved`,
`legal_review_required`, `permission_required`, and `prohibited` all fail.

Validate the catalog and check an intended operation before ingestion:

```bash
urban-growth-sources verify-licenses
urban-growth-sources check-license \
  --source-id ec_ghsl_ucdb_r2024a_v1_2 \
  --use internal_commercial_use
```

## Current production posture

| Source family | Internal commercial use | Controlling point |
|---|---|---|
| GHSL R2024A/R2023A | Permitted | CC BY 4.0; release-specific methodology and product citations required |
| WUP 2018/2025 | Legal review required | CC BY 3.0 IGO does not expressly cover sui generis database rights |
| WPP 2024 | Unresolved | Do not infer its terms from WUP |
| MAP accessibility 2015 | Unresolved | Exact raster terms have not been captured |
| OECD FUA | Unresolved | Exact product and upstream geometry terms have not been captured |
| WorldPop Global 2 | Unresolved | Exact acquired product terms have not been captured |
| Natural Earth Admin 0 | Legal review required | Exact release is not yet pinned in the manifest |
| IPUMS International microdata | Prohibited absent written approval | Commercial use and redistribution are prohibited by its agreement |
| IPUMS NHGIS/IHGIS | Permission required | Aggregate products have distinct, operation-specific terms |

The table is a summary only. `data/licenses.json` controls automated decisions.

## Provenance boundary

Public and private repositories are organizational boundaries, not legal ones. Every
acquired file must be registered in `data/manifest.csv` with its exact URL, release,
retrieval date, checksum, and license statement. Downstream lineage must identify all
transformed files, fitted parameters, trained artifacts, tables, and customer outputs
derived from that source.

No IPUMS International records, extracts, aggregates, fitted parameters, trained
artifacts, or other source-specific outputs may enter a commercial pipeline without
written approval from IPUMS and the relevant official statistical authority. General
published methodological knowledge is not automatically "tainted," but any proposed
commercial transfer requires documented review rather than an assumption that
aggregation removes contractual restrictions.

## Attribution

Attribution follows shared licensed or adapted material when the controlling license
requires it. A forecast merely informed by factual inputs is not automatically an
adaptation, but customer deliverables should carry source acknowledgments whenever
licensed data or adaptations are shared and whenever the product-specific terms
require them.

GHSL requires the release-specific peer-reviewed reference and, where applicable, the
specific product publication. A generic GHSL website link is insufficient. WUP
attribution must identify the exact revision, preserve the CC BY 3.0 IGO reference,
identify adaptations, and avoid implying UN endorsement.

## Updating a decision

A licensing change must update `data/licenses.json` and include primary evidence:

1. Pin the exact product and release.
2. Store the controlling terms URL and an immutable snapshot hash where lawful.
3. Record the licensor, rights holder, applicable law or dispute mechanism, and any
   IGO immunity issue.
4. Decide each intended use independently.
5. Store written permission in `approval_reference` when permission is required.
6. Add or update a test proving that the intended operation passes or remains blocked.

This registry is an operational compliance control, not legal advice.

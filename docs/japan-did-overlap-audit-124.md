# Japan DID origin-overlap audit for issue 124

## Purpose

This audit is the acquisition and concordance stage for the Japan validation selected by
`docs/japan-direct-count-validation-124.md`. It does not yet compare GHSL estimates with direct
census counts. It establishes which official Population Census Densely Inhabited Districts (DIDs)
can support that comparison without silently selecting on future population or dropping boundary
failures.

## Registered source

The input universe is the Ministry of Land, Infrastructure, Transport and Tourism (MLIT) National
Land Numerical Information A16 DID product for 2000, 2005, 2010, 2015, and 2020. The 2000 and 2005
releases comprise 47 prefectural archives each; the later releases are nationwide archives. All 97
official archive names and SHA-256 digests are registered in
`results/japan_did_source_sha256.txt`.

The product carries census DID polygons, population, published area, census year, and municipality
identifiers. Legacy DBF text is decoded as Windows-31J (`cp932`); current archives provide UTF-8
metadata. Zero-valued “affiliation undetermined” placeholder records are excluded because they are
not DIDs and have neither a census year nor positive population or area.

## Cohort and concordance rules

- The analysis cohort is fixed at each origin census: population from 25,000 through 100,000,
  inclusive. Endpoint population is never used for cohort membership.
- Every cohort origin remains in the audit denominator, including no-overlap, split, merge, and
  multiple-overlap cases.
- A material overlap is at least 1% of either polygon's equal-area footprint.
- Dynamic identity requires one material origin and one material endpoint plus at least 50% mutual
  overlap.
- Strict stability uses the same one-to-one rule plus at least 99.5% mutual overlap.
- A three-wave persistence interval is eligible only when both adjacent transitions resolve under
  the same rule.

## Local verification result

The implementation dry run against the registered archive bytes produced the following coverage.
Durable empirical CSVs will be registered from the GitHub Actions artifact after the acquisition
workflow runs in GitHub.

| Origin | Origin DIDs | Dynamic identity | Strict stability |
|---:|---:|---:|---:|
| 2000 | 581 | 334 (57.5%) | 54 (9.3%) |
| 2005 | 565 | 374 (66.2%) | 153 (27.1%) |
| 2010 | 578 | 397 (68.7%) | 153 (26.5%) |
| 2015 | 524 | 230 (43.9%) | 26 (5.0%) |

The low strict-stability coverage means a fixed-boundary Japan result would describe a narrow,
selected subset. The next GHSL comparison must therefore report the dynamic-identity result as the
main direct-count benchmark, retain the full origin-denominator coverage table, and use strict
stability as a sensitivity analysis.

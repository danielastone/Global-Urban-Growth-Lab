# GHSL red-team issue #130 empirical result — 2026-09-01

## Status

Issue #130's internal GHSL diagnostics are now empirically executed. They materially narrow the earlier construction-threat story rather than simply confirming every red-team conjecture.

This remains **retrospective, construction-sensitive evidence**. It is not headline-capable or deployable-at-origin evidence, and it is not a substitute for direct census/locality validation.

## Reproducible run

- GitHub Actions workflow: `GHSL red-team issue 130`
- successful run: `33572990885`
- producing empirical code commit: `6645fdff6ed8355053b0d3090a1652e9acaa7728`
- artifact ID: `9825628433`
- artifact SHA-256: `87ab96713d4b5f7e512cb6065da246eec950dc692491e09dc7159dedbc4e9f40`
- official GHSL UCDB R2024A v1.2 and WUP 2025 inputs were downloaded inside the workflow; hashes are registered in `results/ghsl_redteam_130_source_sha256.txt`.

Registered core output hashes from that artifact:

- cross-source model ranking: `41fe9a76bae672bfc99ed9a5f728103b27104f7d83c6716cb50d6c8291ca0134`
- origin-risk-set coverage: `05eaf5e771e91dda0c35d2e40e0eb8b0cd5d2fb36ea26409609b976a230a4102`
- built-up entanglement diagnostic: `c674a1e75bd77c7d76a2c3d60664cbdd3a4e25bdbde2096eeea7498718b5faa4`

## Finding 12 — 2025 survivor universe: confirmed, but not result-flipping

The unfiltered fixed panel contains 11,422 quality-controlled 2025 centres at every origin. After requiring publisher birth year <= origin and population >=50,000 at the origin, the retained **city share** is only:

| Origin | Eligible centres | Share of 11,422 | Population share retained |
|---:|---:|---:|---:|
| 1985 | 6,143 | 53.8% | 89.3% |
| 1990 | 6,692 | 58.6% | 91.0% |
| 1995 | 7,509 | 65.7% | 92.9% |
| 2000 | 8,286 | 72.5% | 94.6% |
| 2005 | 8,984 | 78.7% | 95.9% |
| 2010 | 9,673 | 84.7% | 97.2% |
| 2015 | 10,333 | 90.5% | 98.3% |

Thus the 2025-survivor construction is a large distortion in **entity counts**, especially at early origins, although excluded centres account for a much smaller share of population.

The origin-defined filter does **not** eliminate fixed-footprint persistence. On the filtered fixed sample, persistence MAE remains low, ranging from roughly 0.39 pp in 1985 to 1.13 pp in 2000. The survivor-universe issue is therefore a genuine sample-definition problem, not a complete explanation of the fixed-GHSL persistence result.

## Finding 13 — built-up lineage entanglement: threat remains, proposed mechanism not supported by this proxy

The source lineage remains observationally entangled: GHSL population is a modeled spatial allocation and built-up information enters that construction. But the proposed internal diagnostic does **not** show that population persistence disappears after removing the contemporaneous built-up-growth component.

Across 1985–2015, raw recent/future population-growth correlations range from 0.607 to 0.909. After separately residualizing recent population growth on recent built-up growth and future population growth on future built-up growth, correlations remain 0.597 to 0.910 and are sometimes higher. Persistence coefficients similarly remain substantial and sometimes increase.

Examples:

- 1985 correlation: 0.909 raw -> 0.910 residualized.
- 2000: 0.607 -> 0.597.
- 2015: 0.689 -> 0.726.

The built-up proxy therefore **does not support the strong claim that fixed-GHSL persistence is mainly the built-up allocator showing through**. This test is only a source-process diagnostic, however; it cannot establish that the residual signal is genuine demographic persistence. Direct locality counts remain necessary for that conclusion.

## Finding 14 — pre-2020 WUP/GHSL divergence collapses substantially

The decisive result is the 1985–2015 comparison. WUP 2025 reference-estimate persistence and dynamic-boundary GHSL persistence have strikingly similar error magnitudes at every observed origin:

| Origin | WUP persistence MAE | Dynamic GHSL persistence MAE | Fixed GHSL persistence MAE |
|---:|---:|---:|---:|
| 1985 | 1.002 pp | 1.016 pp | 0.373 pp |
| 1990 | 1.616 pp | 1.635 pp | 1.047 pp |
| 1995 | 1.239 pp | 1.250 pp | 0.682 pp |
| 2000 | 1.598 pp | 1.602 pp | 1.077 pp |
| 2005 | 0.989 pp | 0.988 pp | 0.457 pp |
| 2010 | 1.157 pp | 1.131 pp | 0.646 pp |
| 2015 | 1.356 pp | 1.383 pp | 0.931 pp |

The actual persistence-versus-country ranking also agrees. Using the leave-city-out historical country baseline:

- WUP and dynamic GHSL have the **same MAE winner at all seven origins**.
- Both reverse in 2000: country context beats persistence.
- Both return to persistence wins in 2005, 2010, and 2015 on MAE.
- Their 2000 MAE deltas are +0.265 pp (WUP) and +0.277 pp (dynamic GHSL), respectively.
- Their 2010 RMSE rankings also agree: country context narrowly beats persistence even while persistence wins MAE.

Fixed-footprint GHSL has the same MAE sign pattern, but much lower absolute errors. This identifies **fixed-footprint construction/smoothing as the main source of the unusually strong GHSL error levels**, not a fundamentally different pre-2020 persistence regime.

Accordingly, the earlier framing of WUP-versus-GHSL behavior as unexplained state dependence should be retired. The distinctive disagreement is concentrated in the modeled 2020->2025 endpoint and is more defensibly treated as **publisher/forward-method sensitivity** unless direct observed data show otherwise.

## Finding 15 — reconciliation relabeled

The 2025 fixed/dynamic reconciliation remains useful, but its evidentiary meaning is narrow. Because the fixed 2025 polygon and MTUC 2025 identity are publisher-aligned by construction, the gate validates current-epoch file/key/version integrity. It is **not independent evidence of historical temporal comparability**.

The issue #130 runner now labels the output `current_epoch_file_integrity_not_temporal_comparability`.

## Revised interpretation

The internal GHSL red team supports four narrower conclusions:

1. The fixed archive has a substantial hindsight-survivor problem by city count; origin-defined filtering is required for any threshold-style comparison.
2. That filtering does not remove strong persistence.
3. The simple built-up partialling proxy does not explain away the persistence signal, so the strongest version of the source-entanglement conjecture is rejected by this internal test.
4. Pre-2020 WUP and dynamic GHSL tell almost the same persistence-versus-country story; fixed geometry chiefly makes the series much smoother and the errors much smaller.

The remaining scientific question is external rather than internal: **does persistence of comparable magnitude survive in direct national census/locality histories on defensibly concorded entities?** That is the appropriate non-modeled falsification gate.

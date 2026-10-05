# H1 WUP rolling-origin OOS result — PR B

The preregistered aggregate country-balanced gate passes: relative RMSE improvement is 10.62% (threshold ≥5%) and MAE difference is −0.002421 (threshold ≤0). The row-weighted aggregate also passes. H1 therefore derives to `evidence_supported`; no lifecycle field or gate threshold was manually edited.

Per-origin reversals remain material: 2020 fails both RMSE and MAE under both weighting regimes, and 2000 fails RMSE under row weighting. The aggregate pass is not uniform across origins.

Frozen panel identity: `a38203c78c42c95b27b2850d4c305eee077f132733f6eceb8f8d1d8e75cec9f2`. Performance builder commit: `e3505aad2f1e2682e3e88b3eb98af6140e59efc8`. Freeze construction commit: `88d407928e3a77f6975e0791741cd59ae7b08994`. Source SHA-256: `3a96030d87aec6c1c50f658d5321067d6345e1ab936c5d2854524f972caa75c0`.

Performance rows SHA-256: `a2e0782b7adf5bc20e606834ed41265b0108ce00b16d8096dc1a2aac189ab73a`. Canonical locked summary SHA-256: `b0528643f6c1f2fcf8fdd6bdabf8f33b3f41fd511ac518cf6a316a6b3c8ce840`. The previous committed summary differed only in two last-bit floating-point string renderings (about 10^-18); aggregate metrics, gates, and substantive per-origin conclusions were identical. The exact locked builder serialization is retained as canonical.

Limitation: this is historical pseudo-OOS on harmonized WUP series. Passing this gate does not substitute for external validation against direct-count census observations.

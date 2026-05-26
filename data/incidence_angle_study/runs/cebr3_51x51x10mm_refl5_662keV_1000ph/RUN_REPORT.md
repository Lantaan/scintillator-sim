# Incidence Angle Study Run Report

## Configuration

- Geometry: quadratic/cubic scintillator, 51 x 51 x 10 mm.
- Material: CeBr3 (`/opnovice2/detector/setDetectorMaterial 0`).
- Reflector: enabled, one XY SiPM, no housing; this gives reflector coverage on the five non-SiPM sides.
- Primary: gamma, 662 keV.
- Output: all ntuples and histograms activated.
- Final angles: 0, 15, 30, 45, 60, 75, and 85 deg.
- Primary counts: 1000 photons for 0-75 deg; 5000 photons for 85 deg because the first 1000-photon near-grazing run produced too few measured primary events.

## Archived Outputs

- Per-angle raw CSV outputs and macros: `angle_*deg/`.
- Low-statistics preserved attempt: `angle_85deg_1000ph_lowstats/`.
- Plots and y=0 slice CSVs: `plots/`.
- Lightweight sanity summaries: `sanity/`.

## Reproducible Scripts

- Simulation runner: `scripts/run_incidence_angle_study.sh`.
- Lightweight between-run sanity checks: `scripts/check_incidence_angle_outputs.py`.
- Plot and final evaluation generation: `scripts/plot_incidence_angle_distribution.py`.

## Final Sanity Summary

The final cases all passed the lightweight sanity checks. The key consistency check is that `results_nt_absorption.csv` row counts match the SiPM absorption count parsed from each run log.

Use `plots/incidence_angle_sanity_summary.csv` for the final plotting/evaluation summary. The one-dimensional distribution plots are detector-x slices through the heatmap row nearest `y=0`, not radial distance-from-center histograms.

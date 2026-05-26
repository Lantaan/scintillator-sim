# Spatial Angle Study Run Report

## Configuration

- Geometry: quadratic/cubic scintillator, 51 x 51 x 10 mm.
- Material: CeBr3 (`/opnovice2/detector/setDetectorMaterial 0`).
- Reflector: enabled, one XY SiPM, no housing; reflector coverage is on the five non-SiPM sides.
- Primary: gamma, 662 keV.
- Primary count: 1000 photons per run.
- Output: all ntuples and histograms activated.
- Source z: -9.0 mm, aimed at the front-center point of the detector/reflector stack.

## Angle Definition

The two requested spatial angles are implemented as independent x-z and y-z tilt angles:

`direction = normalize(tan(ax), tan(ay), 1)`

The source x/y position is shifted by `-tan(angle) * distance_to_front` so each beam intersects the front-center point.

## Planned Runtime

The six-case plan used prior 662 keV runtime data from the previous incidence-angle study. Interpolating by effective polar angle gave an estimated total of about 201 minutes, or about 251 minutes with a 25% buffer. This is below the requested 5:30 cap.

## Runs

| ax (deg) | ay (deg) | effective theta (deg) | effective phi (deg) | elapsed (s) |
|---:|---:|---:|---:|---:|
| 0 | 0 | 0.000 | 0.000 | 1466 |
| 45 | 0 | 45.000 | 0.000 | 1946 |
| 0 | 45 | 45.000 | 90.000 | 1894 |
| 30 | 30 | 39.232 | 45.000 | 2172 |
| 45 | 45 | 54.736 | 45.000 | 2405 |
| 60 | 30 | 61.289 | 18.435 | 2500 |

Total simulation runtime was 12383 s, about 3.44 hours.

## Outputs

- Per-case raw CSV outputs and macros: `ax_*deg_ay_*deg/`.
- Lightweight sanity outputs: `sanity/`.
- Final plots and CSVs: `plots/`.
- For each angle pair, `plots/` contains:
  - `*_heatmap_360x360.*`
  - `*_heatmap_lowres_36x36.*`
  - `*_y0_slice_distribution.*`
  - `*_x_projection_360bins.*`

## Sanity

All six cases passed the lightweight checks. The key consistency check is that `results_nt_absorption.csv` row counts match the SiPM absorption count parsed from each run log. No case had detector x/y outside fractions above zero in the final analysis summary.

Use `sanity/spatial_angle_sanity_summary.csv` for the run-level checks and `plots/spatial_angle_analysis_summary.csv` for plot-level metrics.

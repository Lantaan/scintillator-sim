# 1000 keV, 50 Degree Incidence Check

## Configuration

- Geometry: quadratic/cubic scintillator, 51 x 51 x 10 mm.
- Material: CeBr3 (`/opnovice2/detector/setDetectorMaterial 0`).
- Reflector: enabled, one XY SiPM, no housing; reflector coverage is on the five non-SiPM sides.
- Primary: gamma, 1000 keV.
- Angle: 50 deg.
- Primary count: 1000 photons.
- Output: all ntuples and histograms activated.

## Outputs

- Raw CSV outputs and macro: `angle_50deg/`.
- Plots, y=0 slice CSV, low-resolution heatmap, x-axis projections, and final summary: `plots/`.
- X-axis projection outputs integrate counts over the full detector y extent and write density as counts / gamma / cm^2. Both native 360-bin and 10x wider 36-bin versions are included.
- The low-resolution heatmap y=0 slice is written as `angle_50deg_y0_slice_lowres_36x36.*`; for the 36-bin heatmap the selected y interval is -1.4166667 to 0 mm.
- Lightweight sanity outputs: `sanity/`.

## Sanity

The run passed the lightweight sanity checks. The absorption ntuple row count matches the parsed SiPM absorption count from the run log.

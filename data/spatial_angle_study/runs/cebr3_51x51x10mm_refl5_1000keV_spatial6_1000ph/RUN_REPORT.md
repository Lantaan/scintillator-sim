# Spatial Angle Study: 1000 keV

Run label: `cebr3_51x51x10mm_refl5_1000keV_spatial6_1000ph`

Configuration:

- Detector: CeBr3, 51 x 51 x 10 mm, reflector enabled on 5 sides
- SiPM layout: one XY SiPM plane
- Primary particle: gamma
- Energy: 1000 keV
- Events per case: 1000
- Output mode: all ntuples/histograms activated by `scripts/run_spatial_angle_study.sh`
- Angle pairs: `(0,0)`, `(45,0)`, `(0,45)`, `(30,30)`, `(45,45)`, `(60,30)`

Runtime:

- Total elapsed simulation time: 15830 s, about 4.40 h
- Per-case elapsed range: 1858-3219 s
- Output files: 15 result CSV files per case
- Total result CSV bytes across cases: 2382272937

Sanity:

- Full combined sanity check: passed for all 6 cases
- Status code: 0 for all cases
- Absorption rows match the run-log SiPM absorption counts
- 360x360 heatmap occupancy: 1.0 for all cases
- Detector outside-hit fractions: 0.0 in x and y for all cases
- Analysis sanity flags: none

Generated analysis products:

- `plots/*_heatmap_360x360.csv` and `.png`
- `plots/*_heatmap_lowres_36x36.csv` and `.png`
- `plots/*_y0_slice_distribution.csv` and `.png`
- `plots/*_x_projection_360bins.csv` and `.png`
- `plots/spatial_angle_analysis_summary.csv`
- `sanity/spatial_angle_sanity_summary.csv`

The 360x360 heatmaps from this run were added to `data/heatmap_interpolator/heatmap_index_360.npz`.

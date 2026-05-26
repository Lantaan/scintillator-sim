# Heatmap Interpolator UI

This local tool interpolates already-generated SiPM heatmap data without rerunning Geant4.

## Quick Start

From the repository root:

```powershell
python scripts\build_heatmap_interpolator_index.py --out data\heatmap_interpolator\heatmap_index_360.npz
python scripts\run_heatmap_interpolator_ui.py --host 127.0.0.1 --port 8765
```

Then open:

```text
http://127.0.0.1:8765
```

The server runs in the foreground. Stop it with `Ctrl+C`.

If you already have the UI server running and only changed static UI files, refresh the browser page. If you rebuilt the cache, restart the server so it reloads the `.npz`.

## Build the Cache

```powershell
python scripts\build_heatmap_interpolator_index.py --out data\heatmap_interpolator\heatmap_index_360.npz
```

The cache stores unique generated heatmaps as 360x360 `float32` density arrays in counts / gamma / cm^2. It also stores low-resolution dense flow fields and optimal-transport maps between cached samples for morphing interpolation. Source preference is:

1. Existing 360x360 numeric heatmap CSV.
2. A 360x360 heatmap rebuilt from archived `results_nt_absorption.csv`.
3. Lower-resolution heatmap CSV fallback.

This avoids displaying blocky upsampled 36x36 heatmaps when raw absorption data is available.

By default the cache builder computes 90x90 flow fields and 48x48 optimal-transport maps:

```powershell
python scripts\build_heatmap_interpolator_index.py --out data\heatmap_interpolator\heatmap_index_360.npz --flow-bins 90 --ot-bins 48
```

Use `--skip-flow` or `--skip-ot` if you want to omit one of the morphing modes.

## Run the UI Separately

```powershell
python scripts\run_heatmap_interpolator_ui.py --host 127.0.0.1 --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

## Live Interaction

The theta and phi sliders update on `input` events while dragging. The browser keeps one interpolation request in flight at a time and immediately renders the newest queued slider state when the previous response finishes. This keeps the UI responsive without piling up stale requests.

## Interpolation Modes

- `Hybrid foreground OT`: default. Uses precomputed optimal-transport maps only in the high-density foreground/core, while the diffuse sides/background come from the original intensity blend. A smooth mask feathers between the two and the result is normalized back to the blended total density.
- `Pure optimal transport`: uses precomputed entropic Sinkhorn barycentric transport maps to move density between neighboring heatmaps before blending. This is useful for comparison, but it can show edge-stretching artifacts in sparse or low-density regions.
- `Flow morph`: uses precomputed dense flow fields to warp each contributing heatmap toward the requested intermediate point before blending. This is meant to reduce duplicate-peak artifacts when a peak moves, stretches, or skews between simulated samples.
- `Intensity blend`: the original inverse-distance weighted pixel blend. This is very fast and useful as a baseline, but it can show two peaks when neighboring heatmaps have peaks at different positions.

The flow fields are computed on smoothed log-density heatmaps using a Horn-Schunck style dense optical-flow solve. The optimal-transport maps are computed on clipped/smoothed density heatmaps using an entropic Sinkhorn solve. During UI interaction the server only combines precomputed maps, warps the selected 360x360 heatmaps, applies the selected blend/mask logic, and returns a binary `Float32Array`.

Energy mismatch is weighted strongly in neighbor selection. The default energy distance scale is 200 keV, so heatmaps from a different energy are suppressed much more aggressively than they would be with a full-dataset energy-span scale. You can override this at server start with `--energy-scale`.

## Inputs

- Photon energy in keV, controlled by either the numeric field or the energy slider.
- Polar theta angle in degrees.
- Azimuth phi angle in degrees.
- Neighbor count for inverse-distance interpolation.

The current generated dataset contains 24 cached heatmaps: 6 spatial-angle samples at 200 keV, 11 samples at 662 keV, and 7 samples at 1000 keV. The UI shows which cached heatmaps contributed to each interpolation.

## Add New Data

1. Run new simulations with the project scripts and archive the outputs under `data/`.
2. Make sure each completed case has `run_status.txt` with `status=0`, `energy_keV`, and `beam_on`.
3. Keep `results_nt_absorption.csv` in the case directory. This is the preferred source because the cache builder can rebuild a 360x360 heatmap from it.
4. Rebuild the interpolation cache:

```powershell
python scripts\build_heatmap_interpolator_index.py --out data\heatmap_interpolator\heatmap_index_360.npz
```

5. Restart the UI server and refresh the browser.

Recognized case layouts:

- Incidence-angle cases: `angle_<theta>deg/results_nt_absorption.csv`. These are interpreted as `phi=0`.
- Spatial-angle cases: `ax_<x_angle>deg_ay_<y_angle>deg/results_nt_absorption.csv`. These use `effective_polar_theta_deg` and `effective_azimuth_phi_deg` from `run_status.txt`.
- Numeric heatmap CSVs in a run `plots/` directory are also recognized if named like `angle_<theta>deg_heatmap_360x360.csv` or `ax_<x_angle>deg_ay_<y_angle>deg_heatmap_360x360.csv`.

Source preference is always high-resolution numeric heatmap CSV, then a rebuilt 360x360 histogram from `results_nt_absorption.csv`, then lower-resolution heatmap CSV as a fallback.

## API

Metadata:

```text
/api/metadata
```

Binary interpolation endpoint:

```text
/api/interpolate?energy=662&theta=50&phi=30&k=4&mode=hybrid
```

Use `mode=ot` for pure optimal-transport morphing, `mode=flow` for optical-flow morphing, and `mode=blend` for the original intensity blend.

The interpolation endpoint returns a raw 360x360 little-endian `Float32Array`. Response headers include:

- `X-Shape`
- `X-Interp-Ms`
- `X-Exact-Match`
- `X-Mode`
- `X-Requested-Mode`
- `X-Contributors`

Benchmark endpoint:

```text
/api/benchmark?energy=662&theta=50&phi=30&k=4&repeat=500&mode=hybrid
```

Typical local timing observed for `energy=662`, `theta=19.4`, `phi=0`, `k=4`:

- Hybrid foreground OT: about 29 ms median, about 36 ms p95.
- Optimal transport: about 27 ms median, about 47 ms p95.
- Flow morph: about 30 ms median, about 41 ms p95.
- Intensity blend: about 1 ms median.

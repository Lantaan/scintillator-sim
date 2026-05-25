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

The cache stores unique generated heatmaps as 360x360 `float32` density arrays in counts / gamma / cm^2. Source preference is:

1. Existing 360x360 numeric heatmap CSV.
2. A 360x360 heatmap rebuilt from archived `results_nt_absorption.csv`.
3. Lower-resolution heatmap CSV fallback.

This avoids displaying blocky upsampled 36x36 heatmaps when raw absorption data is available.

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

## Inputs

- Photon energy in keV.
- Polar theta angle in degrees.
- Azimuth phi angle in degrees.
- Neighbor count for inverse-distance interpolation.

The current generated dataset is sparse: most points are at 662 keV, with one 1000 keV point at theta 50 deg and phi 0 deg. The UI shows which cached heatmaps contributed to each interpolation.

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
/api/interpolate?energy=662&theta=50&phi=30&k=4
```

The interpolation endpoint returns a raw 360x360 little-endian `Float32Array`. Response headers include:

- `X-Shape`
- `X-Interp-Ms`
- `X-Exact-Match`
- `X-Contributors`

Benchmark endpoint:

```text
/api/benchmark?energy=662&theta=50&phi=30&k=4&repeat=500
```

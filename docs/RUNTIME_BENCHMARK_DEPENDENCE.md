# Runtime Benchmark: Parameter Dependence (Fast Sweep)

Date: 2026-05-09

This benchmark measures wall-clock runtime dependence on:

- enabled outputs
- scintillator size
- number of particles (`/run/beamOn`)
- gamma energy (`/gun/energy`)

All runs used the project batch entrypoint:

- `scripts/run_batch.sh`

Macro set used:

- `scripts/macros/benchmark/*.mac`

Raw result table:

- `data/runtime_benchmark/runtime_results.csv`

## Method

- Environment: WSL Ubuntu, Geant4 batch mode.
- Timing metric: wall time in seconds (`date +%s` before/after each run).
- Output metric: number of generated `data/results_*.csv` files and their total bytes.
- Each case was run once (quick exploratory benchmark).
- Particle counts were intentionally small (`50` to `500`) to keep runtime short.

## Measured Results

| Group     | Case    | beamOn | Energy (keV) | Size (mm) | Output mode | Wall time (s) | Output files | Output bytes |
|-----------|---------|-------:|-------------:|----------:|-------------|--------------:|-------------:|-------------:|
| outputs   | minimal |    100 |          662 |        51 | minimal     |             5 |            0 |            0 |
| outputs   | all     |    100 |          662 |        51 | all         |            11 |           10 |       849821 |
| size      | small   |    100 |          662 |        20 | minimal     |             6 |            0 |            0 |
| size      | medium  |    100 |          662 |        51 | minimal     |             4 |            0 |            0 |
| size      | large   |    100 |          662 |        80 | minimal     |             4 |            0 |            0 |
| particles | p50     |     50 |          662 |        51 | minimal     |             4 |            0 |            0 |
| particles | p100    |    100 |          662 |        51 | minimal     |             5 |            0 |            0 |
| particles | p200    |    200 |          662 |        51 | minimal     |             8 |            0 |            0 |
| particles | p500    |    500 |          662 |        51 | minimal     |            13 |            0 |            0 |
| energy    | e20     |    100 |           20 |        51 | minimal     |             2 |            0 |            0 |
| energy    | e100    |    100 |          100 |        51 | minimal     |             4 |            0 |            0 |
| energy    | e500    |    100 |          500 |        51 | minimal     |             6 |            0 |            0 |
| energy    | e1000   |    100 |         1000 |        51 | minimal     |             5 |            0 |            0 |

## Trends and Relations

### 1) Output activation dominates runtime and I/O

At fixed physics settings (`beamOn=100`, `662 keV`, `51 mm`):

- `minimal`: 5 s, 0 files, 0 bytes
- `all`: 11 s, 10 files, 849821 bytes

Relation:

- runtime ratio `all/minimal = 11/5 = 2.2x`
- enabling all outputs causes a large I/O jump and roughly doubles runtime in this small-run regime.

Interpretation:

- output writing is a first-order cost driver.
- for performance studies, only enable needed ntuples/histograms.

### 2) Particle count shows near-linear scaling

Using the particle sweep (`50, 100, 200, 500`):

- 50 -> 4 s
- 100 -> 5 s
- 200 -> 8 s
- 500 -> 13 s

Observed relation:

- runtime increases monotonically with particle count.
- scaling is approximately linear with a fixed overhead.

A simple fit from these points is roughly:

- `T(N) ~ T0 + k*N`, with `T0` a few seconds and `k` about `0.02 s/event` order of magnitude in this setup.

Practical projection (same setup):

- `1000` particles would likely land around `20-30 s`.

### 3) Energy changes runtime moderately, non-strictly monotonic at top end

At fixed `beamOn=100`, `size=51 mm`, minimal output:

- 20 keV -> 2 s
- 100 keV -> 4 s
- 500 keV -> 6 s
- 1000 keV -> 5 s

Relation:

- clear increase from low to mid/high energies.
- slight drop at 1000 keV vs 500 keV in this single-run sample; likely stochastic/statistical variation at low event count.

Interpretation:

- higher energy generally means more interactions/secondaries and longer tracking, but small-count noise can reorder adjacent points.

### 4) Scintillator XY size effect is weak in this low-count, minimal-output setup

At fixed `beamOn=100`, `662 keV`, minimal output:

- 20 mm -> 6 s
- 51 mm -> 4 s
- 80 mm -> 4 s

Relation:

- no stable monotonic trend across these three quick runs.
- geometry-size influence appears smaller than output/particle effects at this short-run resolution.

Interpretation:

- with only 100 primaries and minimal output, run-to-run noise and fixed startup overhead can hide geometric scaling.
- size dependence likely exists physically, but needs either more particles or repeated runs for clean separation.

## Important Observation About "minimal" output mode

In this benchmark, minimal mode generated no `results_*.csv` files in the measured runs.

This is consistent with a mode where activated ntuples only write files when rows are produced, and these short runs may produce no rows for that activated channel.

This does not invalidate runtime timing, but it means I/O metrics for minimal mode are effectively zero here.

## Recommended Use for Fast Planning

- For quick iteration:
    - use `beamOn=100` and minimal output macros.
- For runtime extrapolation by count:
    - use the particle-scaling relation as first estimate.
- For physically robust size/energy comparisons:
    - repeat each case 3-5 times and/or increase to `beamOn=500-1000`.

## Reproduce

Run all benchmark cases and regenerate CSV:

```bash
./scripts/run_runtime_benchmark.sh
```

Output:

- `data/runtime_benchmark/runtime_results.csv`
- per-case archived outputs in `data/runtime_benchmark/cases/`

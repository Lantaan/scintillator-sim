#!/usr/bin/env python3
"""Generate lower-resolution heatmaps for incidence-angle absorption data."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from plot_incidence_angle_distribution import (  # noqa: E402
    angle_slug,
    case_dirs,
    choose_heatmap_bins,
    load_absorption_ntuple,
    parse_angle_from_case,
)


def write_heatmap_csv(path: Path, hist: np.ndarray, x_edges: np.ndarray, y_edges: np.ndarray) -> None:
    x_centers = 0.5 * (x_edges[:-1] + x_edges[1:])
    y_centers = 0.5 * (y_edges[:-1] + y_edges[1:])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["x_mm", "y_mm", "count"])
        for ix, x in enumerate(x_centers):
            for iy, y in enumerate(y_centers):
                writer.writerow([f"{x:.8g}", f"{y:.8g}", f"{hist[ix, iy]:.8g}"])


def plot_case(case_dir: Path, out_dir: Path, factor: float) -> None:
    angle = parse_angle_from_case(case_dir)
    data = load_absorption_ntuple(case_dir / "results_nt_absorption.csv")
    base_bins = choose_heatmap_bins(data.x, data.y)
    low_bins = max(4, int(round(base_bins / factor)))
    hist, x_edges, y_edges = np.histogram2d(data.x, data.y, bins=low_bins)

    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"angle_{angle_slug(angle)}deg_heatmap_lowres_{low_bins}x{low_bins}"
    write_heatmap_csv(out_dir / f"{prefix}.csv", hist, x_edges, y_edges)

    fig, ax = plt.subplots(figsize=(5.8, 5.0), constrained_layout=True)
    visible_hist = np.ma.masked_less_equal(hist.T, 0)
    norm = LogNorm(vmin=1, vmax=max(1.0, float(hist.max())))
    mesh = ax.pcolormesh(x_edges, y_edges, visible_hist, shading="auto", cmap="magma", norm=norm)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("detector x (mm)")
    ax.set_ylabel("detector y (mm)")
    ax.set_title(f"Incidence angle {angle:g} deg: low-res SiPM heatmap ({low_bins}x{low_bins})")
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.set_label("measured photon count (log scale)")
    fig.savefig(out_dir / f"{prefix}.png", dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True, help="Archived run root containing angle_*deg directories.")
    parser.add_argument("--angle", help="Only process one angle, e.g. 45.")
    parser.add_argument("--out-dir", type=Path, help="Output directory. Defaults to RUN_ROOT/plots.")
    parser.add_argument("--factor", type=float, default=10.0, help="Resolution reduction factor per axis.")
    args = parser.parse_args()

    if args.factor <= 0:
        raise ValueError("--factor must be positive")

    run_root = args.run_root.resolve()
    out_dir = (args.out_dir or (run_root / "plots")).resolve()
    for case_dir in case_dirs(run_root, args.angle):
        if not case_dir.exists():
            raise FileNotFoundError(f"Missing case directory: {case_dir}")
        plot_case(case_dir, out_dir, args.factor)


if __name__ == "__main__":
    main()

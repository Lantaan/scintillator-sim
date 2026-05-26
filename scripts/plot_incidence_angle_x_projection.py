#!/usr/bin/env python3
"""Generate x-axis projections from incidence-angle SiPM absorption data."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
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
    read_status,
)


def write_projection_csv(
    path: Path,
    x_centers_mm: np.ndarray,
    counts: np.ndarray,
    density_per_gamma_cm2: np.ndarray,
    x_edges_mm: np.ndarray,
    y_width_mm: float,
    beam_on: float,
) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "x_mm",
                "counts_integrated_over_y",
                "density_counts_per_gamma_cm2",
                "x_low_mm",
                "x_high_mm",
                "y_width_mm",
                "beam_on",
            ]
        )
        for i, x in enumerate(x_centers_mm):
            writer.writerow(
                [
                    f"{x:.8g}",
                    f"{counts[i]:.8g}",
                    f"{density_per_gamma_cm2[i]:.8g}",
                    f"{x_edges_mm[i]:.8g}",
                    f"{x_edges_mm[i + 1]:.8g}",
                    f"{y_width_mm:.8g}",
                    f"{beam_on:.8g}",
                ]
            )


def plot_projection(
    path: Path,
    angle: float,
    x_centers_mm: np.ndarray,
    density_per_gamma_cm2: np.ndarray,
    bins: int,
) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    ax.plot(x_centers_mm, density_per_gamma_cm2, color="#185c78", linewidth=1.8)
    ax.set_xlabel("detector x (mm), integrated over y")
    ax.set_ylabel("density (counts / gamma / cm^2)")
    ax.set_title(f"Incidence angle {angle:g} deg: x projection ({bins} bins)")
    ax.grid(True, color="#d7dee2", linewidth=0.7)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def project_case(case_dir: Path, out_dir: Path, factor: float) -> None:
    angle = parse_angle_from_case(case_dir)
    status = read_status(case_dir / "run_status.txt")
    beam_on = float(status.get("beam_on", "1") or 1)
    y_width_mm = float(status.get("detector_side_length_mm", "51") or 51)

    data = load_absorption_ntuple(case_dir / "results_nt_absorption.csv")
    high_bins = choose_heatmap_bins(data.x, data.y)
    wide_bins = max(4, int(round(high_bins / factor)))

    for label, bins in (("highres", high_bins), ("widebin", wide_bins)):
        counts, x_edges_mm = np.histogram(data.x, bins=bins)
        x_centers_mm = 0.5 * (x_edges_mm[:-1] + x_edges_mm[1:])
        strip_area_cm2 = ((x_edges_mm[1:] - x_edges_mm[:-1]) / 10.0) * (y_width_mm / 10.0)
        density = counts / np.maximum(beam_on * strip_area_cm2, 1e-12)

        prefix = f"angle_{angle_slug(angle)}deg_x_projection_{label}_{bins}bins"
        write_projection_csv(
            out_dir / f"{prefix}.csv",
            x_centers_mm,
            counts.astype(float),
            density.astype(float),
            x_edges_mm,
            y_width_mm,
            beam_on,
        )
        plot_projection(out_dir / f"{prefix}.png", angle, x_centers_mm, density.astype(float), bins)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--angle", help="Only process one angle, e.g. 50.")
    parser.add_argument("--out-dir", type=Path, help="Output directory. Defaults to RUN_ROOT/plots.")
    parser.add_argument("--factor", type=float, default=10.0, help="Wide-bin reduction factor.")
    args = parser.parse_args()

    if args.factor <= 0:
        raise ValueError("--factor must be positive")

    run_root = args.run_root.resolve()
    out_dir = (args.out_dir or (run_root / "plots")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    for case_dir in case_dirs(run_root, args.angle):
        if not case_dir.exists():
            raise FileNotFoundError(f"Missing case directory: {case_dir}")
        project_case(case_dir, out_dir, args.factor)


if __name__ == "__main__":
    main()

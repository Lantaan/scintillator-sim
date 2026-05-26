#!/usr/bin/env python3
"""Plot the y=0 slice from an already-generated low-resolution heatmap CSV."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


def angle_slug(angle: str | float) -> str:
    text = f"{float(angle):g}" if not isinstance(angle, str) else angle
    return text.replace(".", "p").replace("-", "m")


def parse_heatmap_name(path: Path) -> tuple[float, int, int]:
    match = re.match(r"angle_([0-9pm.-]+)deg_heatmap_lowres_([0-9]+)x([0-9]+)\.csv$", path.name)
    if not match:
        raise ValueError(f"Cannot parse low-res heatmap name: {path.name}")
    angle = float(match.group(1).replace("p", ".").replace("m", "-"))
    return angle, int(match.group(2)), int(match.group(3))


def infer_edges(centers: np.ndarray) -> np.ndarray:
    if len(centers) == 0:
        return np.asarray([], dtype=float)
    if len(centers) == 1:
        half_width = 0.5
        return np.asarray([centers[0] - half_width, centers[0] + half_width], dtype=float)
    midpoints = 0.5 * (centers[:-1] + centers[1:])
    first = centers[0] - (midpoints[0] - centers[0])
    last = centers[-1] + (centers[-1] - midpoints[-1])
    return np.concatenate([[first], midpoints, [last]]).astype(float)


def read_heatmap_csv(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows: list[tuple[float, float, float]] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append((float(row["x_mm"]), float(row["y_mm"]), float(row["count"])))

    x_centers = np.asarray(sorted({x for x, _, _ in rows}), dtype=float)
    y_centers = np.asarray(sorted({y for _, y, _ in rows}), dtype=float)
    hist = np.zeros((len(x_centers), len(y_centers)), dtype=float)
    x_index = {x: i for i, x in enumerate(x_centers)}
    y_index = {y: i for i, y in enumerate(y_centers)}
    for x, y, count in rows:
        hist[x_index[x], y_index[y]] = count
    return x_centers, y_centers, hist


def choose_y0_bin(y_edges: np.ndarray, y_centers: np.ndarray) -> int:
    containing = np.where((y_edges[:-1] <= 0.0) & (0.0 <= y_edges[1:]))[0]
    if len(containing):
        return int(containing[0])
    return int(np.argmin(np.abs(y_centers)))


def write_slice_csv(path: Path, x_centers: np.ndarray, counts: np.ndarray, y_low: float, y_high: float) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["x_mm", "counts_at_lowres_y0_slice", "slice_y_low_mm", "slice_y_high_mm"])
        for x, count in zip(x_centers, counts):
            writer.writerow([f"{x:.8g}", f"{count:.8g}", f"{y_low:.8g}", f"{y_high:.8g}"])


def plot_slice(
    path: Path,
    angle: float,
    x_centers: np.ndarray,
    counts: np.ndarray,
    y_low: float,
    y_high: float,
    x_bins: int,
) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    ax.plot(x_centers, counts, color="#185c78", linewidth=2.0, marker="o", markersize=3.2)
    ax.set_xlabel("detector x from low-res heatmap y=0 slice (mm)")
    ax.set_ylabel("measured intensity (counts)")
    ax.set_title(f"Incidence angle {angle:g} deg: low-res y=0 slice ({x_bins} bins)")
    ax.text(
        0.02,
        0.95,
        f"y bin: {y_low:.3g} to {y_high:.3g} mm",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        color="#334",
    )
    ax.grid(True, color="#d7dee2", linewidth=0.7)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def process_heatmap(path: Path, out_dir: Path) -> None:
    angle, x_bins, y_bins = parse_heatmap_name(path)
    x_centers, y_centers, hist = read_heatmap_csv(path)
    y_edges = infer_edges(y_centers)
    y_idx = choose_y0_bin(y_edges, y_centers)
    counts = hist[:, y_idx]
    y_low = float(y_edges[y_idx])
    y_high = float(y_edges[y_idx + 1])

    prefix = f"angle_{angle_slug(angle)}deg_y0_slice_lowres_{x_bins}x{y_bins}"
    write_slice_csv(out_dir / f"{prefix}.csv", x_centers, counts, y_low, y_high)
    plot_slice(out_dir / f"{prefix}.png", angle, x_centers, counts, y_low, y_high, x_bins)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--angle", help="Only process one angle, e.g. 50.")
    parser.add_argument("--bins", default="36x36", help="Low-res heatmap size suffix, e.g. 36x36.")
    parser.add_argument("--out-dir", type=Path, help="Output directory. Defaults to RUN_ROOT/plots.")
    args = parser.parse_args()

    run_root = args.run_root.resolve()
    out_dir = (args.out_dir or (run_root / "plots")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.angle is not None:
        paths = [out_dir / f"angle_{angle_slug(args.angle)}deg_heatmap_lowres_{args.bins}.csv"]
    else:
        paths = sorted(out_dir.glob(f"angle_*deg_heatmap_lowres_{args.bins}.csv"))

    if not paths:
        raise FileNotFoundError(f"No low-res heatmap CSVs found in {out_dir} for {args.bins}")

    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Missing low-res heatmap CSV: {path}")
        process_heatmap(path, out_dir)


if __name__ == "__main__":
    main()

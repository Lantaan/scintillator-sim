#!/usr/bin/env python3
"""Generate heatmaps, y=0 slices, and x projections for spatial-angle runs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np


@dataclass
class NtupleData:
    event_id: np.ndarray
    x: np.ndarray
    y: np.ndarray


def angle_slug(angle: str | float) -> str:
    text = f"{float(angle):g}" if not isinstance(angle, str) else angle
    return text.replace(".", "p").replace("-", "m")


def case_name(ax: str | float, ay: str | float) -> str:
    return f"ax_{angle_slug(ax)}deg_ay_{angle_slug(ay)}deg"


def parse_case(case_dir: Path) -> tuple[float, float]:
    match = re.search(r"ax_([0-9pm.-]+)deg_ay_([0-9pm.-]+)deg$", case_dir.name)
    if not match:
        raise ValueError(f"Cannot parse spatial angles from {case_dir}")
    ax = float(match.group(1).replace("p", ".").replace("m", "-"))
    ay = float(match.group(2).replace("p", ".").replace("m", "-"))
    return ax, ay


def case_dirs(run_root: Path, ax: str | None, ay: str | None) -> list[Path]:
    if ax is not None or ay is not None:
        if ax is None or ay is None:
            raise ValueError("--ax and --ay must be provided together")
        return [run_root / case_name(ax, ay)]
    return sorted((p for p in run_root.glob("ax_*deg_ay_*deg") if p.is_dir()), key=parse_case)


def read_status(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def load_absorption_ntuple(path: Path) -> NtupleData:
    event_ids: list[int] = []
    xs: list[float] = []
    ys: list[float] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(line for line in f if not line.startswith("#"))
        for row in reader:
            if len(row) < 3:
                continue
            event_ids.append(int(float(row[0])))
            xs.append(float(row[1]))
            ys.append(float(row[2]))
    return NtupleData(
        event_id=np.asarray(event_ids, dtype=np.int32),
        x=np.asarray(xs, dtype=np.float64),
        y=np.asarray(ys, dtype=np.float64),
    )


def heatmap_metrics(hist: np.ndarray) -> dict[str, float]:
    total_bins = hist.size
    occupied = int(np.count_nonzero(hist))
    positive = hist[hist > 0]
    max_count = float(hist.max()) if hist.size else 0.0
    median_positive = float(np.median(positive)) if positive.size else 0.0
    mean_positive = float(np.mean(positive)) if positive.size else 0.0
    occupancy = occupied / total_bins if total_bins else 0.0
    max_to_median = max_count / median_positive if median_positive > 0 else float("inf")
    probabilities = positive / positive.sum() if positive.size and positive.sum() > 0 else np.array([])
    entropy = float(-(probabilities * np.log2(probabilities)).sum()) if probabilities.size else 0.0
    max_entropy = math.log2(total_bins) if total_bins > 1 else 0.0
    return {
        "heatmap_bins": float(hist.shape[0]) if hist.ndim == 2 else 0.0,
        "heatmap_occupied_bins": float(occupied),
        "heatmap_total_bins": float(total_bins),
        "heatmap_occupancy_fraction": float(occupancy),
        "heatmap_max_count": max_count,
        "heatmap_median_positive_count": median_positive,
        "heatmap_mean_positive_count": mean_positive,
        "heatmap_max_to_median_positive": float(max_to_median),
        "heatmap_entropy_fraction": entropy / max_entropy if max_entropy > 0 else 0.0,
    }


def write_heatmap_csv(path: Path, hist: np.ndarray, x_edges: np.ndarray, y_edges: np.ndarray) -> None:
    x_centers = 0.5 * (x_edges[:-1] + x_edges[1:])
    y_centers = 0.5 * (y_edges[:-1] + y_edges[1:])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["x_mm", "y_mm", "count"])
        for ix, x in enumerate(x_centers):
            for iy, y in enumerate(y_centers):
                writer.writerow([f"{x:.8g}", f"{y:.8g}", f"{hist[ix, iy]:.8g}"])


def plot_heatmap(path: Path, hist: np.ndarray, x_edges: np.ndarray, y_edges: np.ndarray, title: str) -> None:
    fig, ax = plt.subplots(figsize=(5.8, 5.0), constrained_layout=True)
    visible_hist = np.ma.masked_less_equal(hist.T, 0)
    norm = LogNorm(vmin=1, vmax=max(1.0, float(hist.max())))
    mesh = ax.pcolormesh(x_edges, y_edges, visible_hist, shading="auto", cmap="magma", norm=norm)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("detector x (mm)")
    ax.set_ylabel("detector y (mm)")
    ax.set_title(title)
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.set_label("measured photon count (log scale)")
    fig.savefig(path, dpi=180)
    plt.close(fig)


def heatmap_y0_slice(
    hist: np.ndarray,
    x_edges: np.ndarray,
    y_edges: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    x_centers = 0.5 * (x_edges[:-1] + x_edges[1:])
    y_centers = 0.5 * (y_edges[:-1] + y_edges[1:])
    if hist.size == 0 or len(y_centers) == 0:
        return x_centers, np.zeros_like(x_centers), float("nan"), float("nan")
    containing = np.where((y_edges[:-1] <= 0.0) & (0.0 <= y_edges[1:]))[0]
    y_index = int(containing[0]) if len(containing) else int(np.argmin(np.abs(y_centers)))
    return x_centers, hist[:, y_index].astype(float), float(y_edges[y_index]), float(y_edges[y_index + 1])


def write_y0_slice_csv(path: Path, x_centers: np.ndarray, counts: np.ndarray, y_low: float, y_high: float) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["x_mm", "counts_at_y0_slice", "slice_y_low_mm", "slice_y_high_mm"])
        for x, count in zip(x_centers, counts):
            writer.writerow([f"{x:.8g}", f"{count:.8g}", f"{y_low:.8g}", f"{y_high:.8g}"])


def plot_y0_slice(path: Path, x_centers: np.ndarray, counts: np.ndarray, title: str) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    ax.plot(x_centers, counts, color="#185c78", linewidth=1.8)
    ax.set_xlabel("detector x at y=0 slice (mm)")
    ax.set_ylabel("measured intensity (counts)")
    ax.set_title(title)
    ax.grid(True, color="#d7dee2", linewidth=0.7)
    fig.savefig(path, dpi=180)
    plt.close(fig)


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


def plot_projection(path: Path, x_centers_mm: np.ndarray, density_per_gamma_cm2: np.ndarray, title: str) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    ax.plot(x_centers_mm, density_per_gamma_cm2, color="#185c78", linewidth=1.8)
    ax.set_xlabel("detector x (mm), integrated over y")
    ax.set_ylabel("density (counts / gamma / cm^2)")
    ax.set_title(title)
    ax.grid(True, color="#d7dee2", linewidth=0.7)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def make_histogram(data: NtupleData, bins: int, width_mm: float, length_mm: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    hist, x_edges, y_edges = np.histogram2d(
        data.x,
        data.y,
        bins=bins,
        range=[[-width_mm / 2.0, width_mm / 2.0], [-length_mm / 2.0, length_mm / 2.0]],
    )
    return hist, x_edges, y_edges


def process_case(case_dir: Path, out_dir: Path) -> dict[str, float | str | list[str]]:
    ax, ay = parse_case(case_dir)
    status = read_status(case_dir / "run_status.txt")
    beam_on = float(status.get("beam_on", "1") or 1)
    width_mm = float(status.get("detector_width_mm", "51") or 51)
    length_mm = float(status.get("detector_side_length_mm", "51") or 51)
    theta_eff = float(status.get("effective_polar_theta_deg", "nan"))
    phi_eff = float(status.get("effective_azimuth_phi_deg", "nan"))

    data = load_absorption_ntuple(case_dir / "results_nt_absorption.csv")
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = case_name(ax, ay)
    label = f"ax {ax:g} deg, ay {ay:g} deg"

    high_bins = 360
    low_bins = 36
    high_hist, high_x_edges, high_y_edges = make_histogram(data, high_bins, width_mm, length_mm)
    low_hist, low_x_edges, low_y_edges = make_histogram(data, low_bins, width_mm, length_mm)

    write_heatmap_csv(out_dir / f"{slug}_heatmap_360x360.csv", high_hist, high_x_edges, high_y_edges)
    plot_heatmap(
        out_dir / f"{slug}_heatmap_360x360.png",
        high_hist,
        high_x_edges,
        high_y_edges,
        f"{label}: SiPM heatmap (360x360)",
    )

    write_heatmap_csv(out_dir / f"{slug}_heatmap_lowres_36x36.csv", low_hist, low_x_edges, low_y_edges)
    plot_heatmap(
        out_dir / f"{slug}_heatmap_lowres_36x36.png",
        low_hist,
        low_x_edges,
        low_y_edges,
        f"{label}: low-res SiPM heatmap (36x36)",
    )

    x_slice, y0_counts, y0_low, y0_high = heatmap_y0_slice(high_hist, high_x_edges, high_y_edges)
    write_y0_slice_csv(out_dir / f"{slug}_y0_slice_distribution.csv", x_slice, y0_counts, y0_low, y0_high)
    plot_y0_slice(out_dir / f"{slug}_y0_slice_distribution.png", x_slice, y0_counts, f"{label}: y=0 slice")

    counts, x_edges = np.histogram(data.x, bins=high_bins, range=(-width_mm / 2.0, width_mm / 2.0))
    x_centers = 0.5 * (x_edges[:-1] + x_edges[1:])
    strip_area_cm2 = ((x_edges[1:] - x_edges[:-1]) / 10.0) * (length_mm / 10.0)
    density = counts / np.maximum(beam_on * strip_area_cm2, 1e-12)
    write_projection_csv(
        out_dir / f"{slug}_x_projection_360bins.csv",
        x_centers,
        counts.astype(float),
        density.astype(float),
        x_edges,
        length_mm,
        beam_on,
    )
    plot_projection(out_dir / f"{slug}_x_projection_360bins.png", x_centers, density.astype(float), f"{label}: x projection (360 bins)")

    outside_x = float(np.mean(np.abs(data.x) > width_mm / 2.0)) if len(data.x) else 0.0
    outside_y = float(np.mean(np.abs(data.y) > length_mm / 2.0)) if len(data.y) else 0.0
    metrics: dict[str, float | str | list[str]] = {
        "case": slug,
        "angle_x_deg": ax,
        "angle_y_deg": ay,
        "effective_polar_theta_deg": theta_eff,
        "effective_azimuth_phi_deg": phi_eff,
        "beam_on": beam_on,
        "absorption_rows": float(len(data.x)),
        "unique_events_with_absorption": float(len(np.unique(data.event_id))) if len(data.event_id) else 0.0,
        "x_outside_detector_fraction": outside_x,
        "y_outside_detector_fraction": outside_y,
        "y0_slice_y_low_mm": y0_low,
        "y0_slice_y_high_mm": y0_high,
        **heatmap_metrics(high_hist),
    }
    flags: list[str] = []
    if len(data.x) <= 0:
        flags.append("no SiPM absorption rows found")
    if outside_x > 0.01:
        flags.append("more than 1% of hits are outside configured detector width")
    if outside_y > 0.01:
        flags.append("more than 1% of hits are outside configured detector length")
    if metrics["heatmap_occupancy_fraction"] < 0.05 and len(data.x) > 0:
        flags.append("360x360 heatmap is sparse")
    if metrics["heatmap_max_to_median_positive"] > 100 and metrics["heatmap_occupancy_fraction"] < 0.2:
        flags.append("360x360 heatmap is dominated by isolated hot bins")
    metrics["sanity_flags"] = flags

    with (out_dir / f"{slug}_analysis_sanity.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, sort_keys=True)
    return metrics


def write_summary(rows: list[dict[str, float | str | list[str]]], out_dir: Path) -> None:
    if not rows:
        return
    keys = [
        "case",
        "angle_x_deg",
        "angle_y_deg",
        "effective_polar_theta_deg",
        "effective_azimuth_phi_deg",
        "beam_on",
        "absorption_rows",
        "unique_events_with_absorption",
        "heatmap_occupancy_fraction",
        "heatmap_max_to_median_positive",
        "x_outside_detector_fraction",
        "y_outside_detector_fraction",
        "y0_slice_y_low_mm",
        "y0_slice_y_high_mm",
    ]
    with (out_dir / "spatial_angle_analysis_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys + ["sanity_flags"])
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in keys} | {"sanity_flags": "; ".join(row.get("sanity_flags", []))})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--ax")
    parser.add_argument("--ay")
    parser.add_argument("--out-dir", type=Path, help="Output directory. Defaults to RUN_ROOT/plots.")
    args = parser.parse_args()

    run_root = args.run_root.resolve()
    out_dir = (args.out_dir or (run_root / "plots")).resolve()
    rows = []
    for case_dir in case_dirs(run_root, args.ax, args.ay):
        if not case_dir.exists():
            raise FileNotFoundError(f"Missing case directory: {case_dir}")
        rows.append(process_case(case_dir, out_dir))
    write_summary(rows, out_dir)


if __name__ == "__main__":
    main()

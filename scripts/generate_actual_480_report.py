#!/usr/bin/env python3
"""Generate 480-bin actual-run heatmaps, slices, projections, and peak widths."""

from __future__ import annotations

import argparse
import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ActualCase:
    path: Path
    label: str
    beam_width_mm: float
    angle_deg: float


def slug(value: float) -> str:
    return f"{value:g}".replace(".", "p").replace("-", "m")


def parse_case(path: Path) -> ActualCase:
    match = re.match(r"(?P<beam>[0-9]+(?:[p.][0-9]+)?)mm_(?P<angle>[0-9]+(?:[p.][0-9]+)?)_deg_nt_absorption\.csv$", path.name)
    if not match:
        raise ValueError(f"Cannot parse actual-run case from {path.name}")
    beam_width = float(match.group("beam").replace("p", "."))
    angle = float(match.group("angle").replace("p", "."))
    return ActualCase(
        path=path,
        label=f"beam_{slug(beam_width)}mm_angle_{slug(angle)}deg",
        beam_width_mm=beam_width,
        angle_deg=angle,
    )


def centers(edges: np.ndarray) -> np.ndarray:
    return 0.5 * (edges[:-1] + edges[1:])


def y0_bin(edges: np.ndarray) -> int:
    containing = np.where((edges[:-1] <= 0.0) & (0.0 <= edges[1:]))[0]
    if len(containing):
        return int(containing[0])
    return int(np.argmin(np.abs(centers(edges))))


def raw_peak(x: np.ndarray, y: np.ndarray) -> tuple[float, float, int]:
    idx = int(np.nanargmax(y))
    return float(x[idx]), float(y[idx]), idx


def interpolate_crossing(x1: float, y1: float, x2: float, y2: float, target: float) -> float:
    if y2 == y1:
        return 0.5 * (x1 + x2)
    return x1 + (target - y1) * (x2 - x1) / (y2 - y1)


def hwhm_metrics(x: np.ndarray, y: np.ndarray) -> dict[str, float | bool]:
    peak_x, peak_y, peak_idx = raw_peak(x, y)
    half = 0.5 * peak_y
    left_cross = math.nan
    right_cross = math.nan

    for i in range(peak_idx, 0, -1):
        if y[i - 1] <= half <= y[i] or y[i - 1] >= half >= y[i]:
            left_cross = interpolate_crossing(float(x[i - 1]), float(y[i - 1]), float(x[i]), float(y[i]), half)
            break

    for i in range(peak_idx, len(x) - 1):
        if y[i] >= half >= y[i + 1] or y[i] <= half <= y[i + 1]:
            right_cross = interpolate_crossing(float(x[i]), float(y[i]), float(x[i + 1]), float(y[i + 1]), half)
            break

    left_hwhm = peak_x - left_cross if math.isfinite(left_cross) else math.nan
    right_hwhm = right_cross - peak_x if math.isfinite(right_cross) else math.nan
    fwhm = right_cross - left_cross if math.isfinite(left_cross) and math.isfinite(right_cross) else math.nan
    return {
        "peak_x_mm": peak_x,
        "peak_count": peak_y,
        "half_max_count": half,
        "left_halfmax_x_mm": left_cross,
        "right_halfmax_x_mm": right_cross,
        "left_hwhm_mm": left_hwhm,
        "right_hwhm_mm": right_hwhm,
        "fwhm_mm": fwhm,
        "has_left_crossing": math.isfinite(left_cross),
        "has_right_crossing": math.isfinite(right_cross),
    }


def write_heatmap_csv(path: Path, hist: np.ndarray, x_edges: np.ndarray, y_edges: np.ndarray) -> None:
    x_centers = centers(x_edges)
    y_centers = centers(y_edges)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["x_mm", "y_mm", "count"])
        for ix, x in enumerate(x_centers):
            for iy, y in enumerate(y_centers):
                writer.writerow([f"{x:.8g}", f"{y:.8g}", f"{float(hist[ix, iy]):.8g}"])


def plot_heatmap(path: Path, hist: np.ndarray, x_edges: np.ndarray, y_edges: np.ndarray, title: str) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 5.2), constrained_layout=True)
    visible = np.ma.masked_less_equal(hist.T, 0)
    norm = LogNorm(vmin=1.0, vmax=max(1.0, float(hist.max())))
    mesh = ax.pcolormesh(x_edges, y_edges, visible, shading="auto", cmap="magma", norm=norm)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("detector x (mm)")
    ax.set_ylabel("detector y (mm)")
    ax.set_title(title)
    cbar = fig.colorbar(mesh, ax=ax)
    cbar.set_label("counts per bin (log scale)")
    fig.savefig(path, dpi=190)
    plt.close(fig)


def write_slice_csv(
    path: Path,
    x_centers: np.ndarray,
    counts: np.ndarray,
    y_low: float,
    y_high: float,
    y_bin_width: float,
) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["x_mm", "count", "slice_y_low_mm", "slice_y_high_mm", "slice_y_bin_width_mm"])
        for x, count in zip(x_centers, counts):
            writer.writerow([f"{x:.8g}", f"{float(count):.8g}", f"{y_low:.8g}", f"{y_high:.8g}", f"{y_bin_width:.8g}"])


def plot_slice(path: Path, x_centers: np.ndarray, counts: np.ndarray, title: str, y_bin_width: float) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    ax.plot(x_centers, counts, color="#185c78", linewidth=1.8)
    ax.set_xlabel("detector x (mm)")
    ax.set_ylabel("counts")
    ax.set_title(title)
    ax.text(
        0.02,
        0.95,
        f"y-bin width: {y_bin_width:.4g} mm",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        color="#334",
    )
    ax.grid(True, color="#d7dee2", linewidth=0.7)
    fig.savefig(path, dpi=190)
    plt.close(fig)


def write_projection_csv(path: Path, x_centers: np.ndarray, counts: np.ndarray, x_edges: np.ndarray, y_width_mm: float) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["x_mm", "count", "x_low_mm", "x_high_mm", "integrated_y_width_mm"])
        for i, x in enumerate(x_centers):
            writer.writerow([f"{x:.8g}", f"{float(counts[i]):.8g}", f"{x_edges[i]:.8g}", f"{x_edges[i + 1]:.8g}", f"{y_width_mm:.8g}"])


def plot_projection(path: Path, x_centers: np.ndarray, counts: np.ndarray, title: str) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
    ax.plot(x_centers, counts, color="#185c78", linewidth=1.8)
    ax.set_xlabel("detector x (mm)")
    ax.set_ylabel("counts")
    ax.set_title(title)
    ax.grid(True, color="#d7dee2", linewidth=0.7)
    fig.savefig(path, dpi=190)
    plt.close(fig)


def process_case(
    case: ActualCase,
    out_dir: Path,
    detector_mm: float,
    bins: int,
    chunksize: int,
    heatmap_csv_only: bool,
) -> list[dict[str, object]]:
    half = detector_mm / 2.0
    edges = np.linspace(-half, half, bins + 1)
    hist = np.zeros((bins, bins), dtype=np.int64)
    projection = np.zeros(bins, dtype=np.int64)
    rows = 0
    finite_rows = 0

    reader = pd.read_csv(
        case.path,
        comment="#",
        header=None,
        names=["event_id", "x", "y"],
        usecols=[0, 1, 2],
        dtype={"event_id": "int32", "x": "float64", "y": "float64"},
        chunksize=chunksize,
    )
    for chunk_index, chunk in enumerate(reader, start=1):
        rows += len(chunk)
        x = chunk["x"].to_numpy()
        y = chunk["y"].to_numpy()
        finite = np.isfinite(x) & np.isfinite(y)
        if not np.all(finite):
            x = x[finite]
            y = y[finite]
        finite_rows += len(x)
        hist += np.histogram2d(x, y, bins=(edges, edges))[0].astype(np.int64)
        projection += np.histogram(x, bins=edges)[0].astype(np.int64)
        print(f"{case.path.name}: processed chunk {chunk_index}, rows={rows}", flush=True)

    x_centers = centers(edges)
    y_centers = centers(edges)
    y_index = y0_bin(edges)
    y_low = float(edges[y_index])
    y_high = float(edges[y_index + 1])
    y_bin_width = y_high - y_low
    slice_counts = hist[:, y_index].astype(float)

    title_prefix = f"{case.beam_width_mm:g} mm beam, {case.angle_deg:g} deg"
    bin_width = detector_mm / bins
    heatmap_title = f"{title_prefix}: {bins}x{bins} bins ({bin_width:.4g} mm/bin)"
    slice_title = f"{title_prefix}: y=0 slice"
    projection_title = f"{title_prefix}: x projection"

    write_heatmap_csv(out_dir / f"{case.label}_heatmap_{bins}x{bins}.csv", hist, edges, edges)
    if heatmap_csv_only:
        return []
    plot_heatmap(out_dir / f"{case.label}_heatmap_{bins}x{bins}.png", hist, edges, edges, heatmap_title)

    write_slice_csv(out_dir / f"{case.label}_y0_slice.csv", x_centers, slice_counts, y_low, y_high, y_bin_width)
    plot_slice(out_dir / f"{case.label}_y0_slice.png", x_centers, slice_counts, slice_title, y_bin_width)

    write_projection_csv(out_dir / f"{case.label}_x_projection.csv", x_centers, projection.astype(float), edges, detector_mm)
    plot_projection(out_dir / f"{case.label}_x_projection.png", x_centers, projection.astype(float), projection_title)

    metric_rows: list[dict[str, object]] = []
    for curve_type, counts in [("slice", slice_counts), ("projection", projection.astype(float))]:
        row: dict[str, object] = {
            "case_label": case.label,
            "curve_type": curve_type,
            "beam_width_mm": case.beam_width_mm,
            "angle_deg": case.angle_deg,
            "rows": rows,
            "finite_rows": finite_rows,
        }
        row.update(hwhm_metrics(x_centers, counts))
        metric_rows.append(row)
    return metric_rows


def write_metrics(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    metric_columns = [
        "case_label",
        "curve_type",
        "beam_width_mm",
        "angle_deg",
        "rows",
        "finite_rows",
        "peak_x_mm",
        "peak_count",
        "half_max_count",
        "left_halfmax_x_mm",
        "right_halfmax_x_mm",
        "left_hwhm_mm",
        "right_hwhm_mm",
        "fwhm_mm",
    ]
    sorted_rows = sorted(rows, key=lambda row: (str(row["curve_type"]), float(row["beam_width_mm"]), float(row["angle_deg"])))
    formatted_rows = []
    for row in sorted_rows:
        formatted_row = {}
        for column in metric_columns:
            value = row[column]
            if isinstance(value, bool):
                formatted_row[column] = value
            elif isinstance(value, (int, float, np.integer, np.floating)):
                formatted_row[column] = "nan" if not math.isfinite(float(value)) else f"{float(value):.2f}"
            else:
                formatted_row[column] = value
        formatted_rows.append(formatted_row)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=metric_columns)
        writer.writeheader()
        writer.writerows(formatted_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--glob", default=str(REPO_ROOT / "data" / "actual" / "*_nt_absorption.csv"), help="Fallback glob when --input is not supplied.")
    parser.add_argument("--input", dest="input_files", type=Path, nargs="+", action="append", help="One or more explicit absorption CSV paths. May be repeated; overrides --glob.")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "data" / "actual" / "analysis_480_report")
    parser.add_argument("--detector-mm", type=float, default=51.0)
    parser.add_argument("--bins", type=int, default=480)
    parser.add_argument("--chunksize", type=int, default=2_000_000)
    parser.add_argument("--heatmap-csv-only", action="store_true", help="Write heatmap CSVs only; skip PNGs, slices, projections, and metrics.")
    args = parser.parse_args()

    if args.input_files:
        files = []
        seen: set[Path] = set()
        for group in args.input_files:
            for input_path in group:
                resolved = input_path.expanduser().resolve()
                if not resolved.is_file():
                    raise FileNotFoundError(f"Input file does not exist: {resolved}")
                if resolved not in seen:
                    files.append(resolved)
                    seen.add(resolved)
    else:
        glob_path = Path(args.glob)
        files = sorted(glob_path.parent.glob(glob_path.name) if glob_path.is_absolute() else Path().glob(args.glob))
    if not files:
        raise FileNotFoundError(f"No input absorption CSV files were selected")
    cases = [parse_case(path.resolve()) for path in files]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    all_metrics: list[dict[str, object]] = []
    for case in sorted(cases, key=lambda item: (item.beam_width_mm, item.angle_deg)):
        all_metrics.extend(
            process_case(
                case,
                args.out_dir.resolve(),
                args.detector_mm,
                args.bins,
                args.chunksize,
                args.heatmap_csv_only,
            )
        )
    if not args.heatmap_csv_only:
        write_metrics(args.out_dir.resolve() / "peak_positions_and_half_widths.csv", all_metrics)
    print(f"Wrote actual-run report outputs to {args.out_dir.resolve()}")


if __name__ == "__main__":
    main()

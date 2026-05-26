#!/usr/bin/env python3
"""Plot and sanity-check incidence-angle SiPM absorption distributions."""

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


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = REPO_ROOT / "data" / "incidence_angle_study" / "runs"


@dataclass
class NtupleData:
    event_id: np.ndarray
    x: np.ndarray
    y: np.ndarray


def angle_slug(angle: str | float) -> str:
    text = f"{float(angle):g}" if not isinstance(angle, str) else angle
    return text.replace(".", "p").replace("-", "m")


def parse_angle_from_case(case_dir: Path) -> float:
    match = re.search(r"angle_([0-9pm.-]+)deg$", case_dir.name)
    if not match:
        raise ValueError(f"Cannot parse angle from {case_dir}")
    return float(match.group(1).replace("p", ".").replace("m", "-"))


def case_dirs(run_root: Path, angle: str | None) -> list[Path]:
    if angle is not None:
        return [run_root / f"angle_{angle_slug(angle)}deg"]
    dirs = [p for p in run_root.glob("angle_*deg") if p.is_dir()]
    return sorted(dirs, key=parse_angle_from_case)


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


def count_ntuple_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line and not line.startswith("#"))


def read_status(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                values[key] = value
    return values


def read_run_summary(log_path: Path) -> dict[str, float]:
    patterns = {
        "events": r"# of primary particles:\s+([0-9]+)",
        "scint_created": r"Total number of scintillation photons created:\s+([0-9]+)",
        "op_absorption": r"OpAbsorption:\s+([0-9]+)",
        "sipm_absorption": r"OpAbsorption in SiPM:\s+([0-9]+)",
        "real_seconds": r"Real=([0-9.]+)s",
    }
    text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    out: dict[str, float] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            out[key] = float(match.group(1))
    return out


def choose_heatmap_bins(x: np.ndarray, y: np.ndarray) -> int:
    n = len(x)
    if n == 0:
        return 128
    raw = int(round(math.sqrt(n / 25.0)))
    return int(np.clip(raw, 128, 360))


def heatmap_metrics(x: np.ndarray, y: np.ndarray, bins: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, float]]:
    hist, x_edges, y_edges = np.histogram2d(x, y, bins=bins)
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
    entropy_fraction = entropy / max_entropy if max_entropy > 0 else 0.0
    metrics = {
        "heatmap_bins": float(bins),
        "heatmap_occupied_bins": float(occupied),
        "heatmap_total_bins": float(total_bins),
        "heatmap_occupancy_fraction": float(occupancy),
        "heatmap_max_count": max_count,
        "heatmap_median_positive_count": median_positive,
        "heatmap_mean_positive_count": mean_positive,
        "heatmap_max_to_median_positive": float(max_to_median),
        "heatmap_entropy_fraction": entropy_fraction,
    }
    return hist, x_edges, y_edges, metrics


def heatmap_y0_slice(
    hist: np.ndarray,
    x_edges: np.ndarray,
    y_edges: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Return the heatmap row whose y-bin contains or is nearest y=0."""
    x_centers = 0.5 * (x_edges[:-1] + x_edges[1:])
    y_centers = 0.5 * (y_edges[:-1] + y_edges[1:])
    if hist.size == 0 or len(y_centers) == 0:
        return x_centers, np.zeros_like(x_centers), float("nan"), float("nan")
    y_index = int(np.argmin(np.abs(y_centers)))
    y_low = float(y_edges[y_index])
    y_high = float(y_edges[y_index + 1])
    return x_centers, hist[:, y_index].astype(float), y_low, y_high


def write_y0_slice_csv(path: Path, x_centers: np.ndarray, counts: np.ndarray, y_low: float, y_high: float) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["x_mm", "counts_at_y0_slice", "slice_y_low_mm", "slice_y_high_mm"])
        for x, c in zip(x_centers, counts):
            writer.writerow([f"{x:.8g}", f"{c:.8g}", f"{y_low:.8g}", f"{y_high:.8g}"])


def sanity_flags(metrics: dict[str, float]) -> list[str]:
    flags: list[str] = []
    n = metrics.get("absorption_rows", 0.0)
    if n <= 0:
        flags.append("no SiPM absorption rows found")
    if metrics.get("phot_count_rows", 0.0) <= 0:
        flags.append("no phot_count rows found")
    occupancy = metrics.get("heatmap_occupancy_fraction", 0.0)
    if occupancy < 0.05 and n > 0:
        flags.append("heatmap very sparse; reduce heatmap bin count")
    if occupancy > 0.98 and metrics.get("heatmap_max_to_median_positive", 0.0) < 2:
        flags.append("heatmap nearly fully occupied; increase heatmap bin count if structure is hidden")
    if metrics.get("heatmap_max_to_median_positive", 0.0) > 100 and occupancy < 0.2:
        flags.append("heatmap dominated by isolated hot bins")
    if metrics.get("unique_events_with_absorption", 0.0) < 50:
        flags.append("few primary events produced measured photons")
    if metrics.get("x_outside_detector_fraction", 0.0) > 0.01:
        flags.append("more than 1% of hits are outside configured detector width")
    if metrics.get("y_outside_detector_fraction", 0.0) > 0.01:
        flags.append("more than 1% of hits are outside configured detector length")
    return flags


def evaluate_case(case_dir: Path, out_dir: Path, make_plots: bool) -> dict[str, float | str | list[str]]:
    angle = parse_angle_from_case(case_dir)
    status = read_status(case_dir / "run_status.txt")
    beam_on = float(status.get("beam_on", "0") or 0)
    detector_width_mm = float(status.get("detector_width_mm", "57.7") or 57.7)
    detector_length_mm = float(status.get("detector_side_length_mm", "57.7") or 57.7)

    absorption_path = case_dir / "results_nt_absorption.csv"
    if not absorption_path.exists():
        raise FileNotFoundError(f"Missing absorption ntuple: {absorption_path}")

    data = load_absorption_ntuple(absorption_path)
    x, y = data.x, data.y
    bins = choose_heatmap_bins(x, y)
    hist, x_edges, y_edges, heat_metrics = heatmap_metrics(x, y, bins)
    x_slice, y0_counts, y0_low, y0_high = heatmap_y0_slice(hist, x_edges, y_edges)
    run_summary = read_run_summary(case_dir / "run.log")

    metrics: dict[str, float | str | list[str]] = {
        "angle_deg": angle,
        "beam_on": beam_on,
        "absorption_rows": float(len(x)),
        "unique_events_with_absorption": float(len(np.unique(data.event_id))) if len(data.event_id) else 0.0,
        "x_min_mm": float(np.min(x)) if len(x) else float("nan"),
        "x_max_mm": float(np.max(x)) if len(x) else float("nan"),
        "y_min_mm": float(np.min(y)) if len(y) else float("nan"),
        "y_max_mm": float(np.max(y)) if len(y) else float("nan"),
        "r_mean_mm": float(np.mean(np.hypot(x, y))) if len(x) else float("nan"),
        "r_p95_mm": float(np.percentile(np.hypot(x, y), 95)) if len(x) else float("nan"),
        "x_outside_detector_fraction": float(np.mean(np.abs(x) > detector_width_mm / 2.0)) if len(x) else 0.0,
        "y_outside_detector_fraction": float(np.mean(np.abs(y) > detector_length_mm / 2.0)) if len(y) else 0.0,
        "phot_count_rows": float(count_ntuple_rows(case_dir / "results_nt_phot_count.csv")) if (case_dir / "results_nt_phot_count.csv").exists() else 0.0,
        "status_rows": float(count_ntuple_rows(case_dir / "results_nt_status.csv")) if (case_dir / "results_nt_status.csv").exists() else 0.0,
        **heat_metrics,
        **run_summary,
    }
    metrics["sanity_flags"] = sanity_flags({k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))})

    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"angle_{angle_slug(angle)}deg"
    write_y0_slice_csv(out_dir / f"{prefix}_y0_slice_distribution.csv", x_slice, y0_counts, y0_low, y0_high)
    with (out_dir / f"{prefix}_sanity.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, sort_keys=True)

    if make_plots:
        fig, ax = plt.subplots(figsize=(7.0, 4.2), constrained_layout=True)
        ax.plot(x_slice, y0_counts, color="#185c78", linewidth=1.8)
        ax.set_xlabel("detector x at y=0 slice (mm)")
        ax.set_ylabel("measured intensity (counts)")
        ax.set_title(f"Incidence angle {angle:g} deg: SiPM photon distribution at y=0")
        ax.grid(True, color="#d7dee2", linewidth=0.7)
        fig.savefig(out_dir / f"{prefix}_y0_slice_distribution.png", dpi=180)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(5.8, 5.0), constrained_layout=True)
        visible_hist = np.ma.masked_less_equal(hist.T, 0)
        norm = LogNorm(vmin=1, vmax=max(1.0, float(hist.max())))
        mesh = ax.pcolormesh(x_edges, y_edges, visible_hist, shading="auto", cmap="magma", norm=norm)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("detector x (mm)")
        ax.set_ylabel("detector y (mm)")
        ax.set_title(f"Incidence angle {angle:g} deg: SiPM photon heatmap")
        cbar = fig.colorbar(mesh, ax=ax)
        cbar.set_label("measured photon count (log scale)")
        fig.savefig(out_dir / f"{prefix}_heatmap.png", dpi=180)
        plt.close(fig)

    return metrics


def write_study_summary(metrics: list[dict[str, float | str | list[str]]], out_dir: Path) -> None:
    if not metrics:
        return
    keys = [
        "angle_deg",
        "beam_on",
        "real_seconds",
        "scint_created",
        "sipm_absorption",
        "absorption_rows",
        "unique_events_with_absorption",
        "phot_count_rows",
        "heatmap_bins",
        "heatmap_occupancy_fraction",
        "heatmap_max_to_median_positive",
        "heatmap_entropy_fraction",
        "r_mean_mm",
        "r_p95_mm",
    ]
    with (out_dir / "incidence_angle_sanity_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys + ["sanity_flags"])
        writer.writeheader()
        for row in metrics:
            writer.writerow({key: row.get(key, "") for key in keys} | {"sanity_flags": "; ".join(row.get("sanity_flags", []))})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True, help="Archived run root containing angle_*deg directories.")
    parser.add_argument("--angle", help="Only process one angle, e.g. 45.")
    parser.add_argument("--out-dir", type=Path, help="Output directory for plots and sanity files.")
    parser.add_argument("--check-only", action="store_true", help="Write sanity data and radial CSVs without PNG plots.")
    parser.add_argument("--write-summary", action="store_true", help="Write combined sanity CSV.")
    args = parser.parse_args()

    run_root = args.run_root.resolve()
    out_dir = (args.out_dir or (run_root / "plots")).resolve()
    metrics: list[dict[str, float | str | list[str]]] = []

    for case_dir in case_dirs(run_root, args.angle):
        if not case_dir.exists():
            raise FileNotFoundError(f"Missing case directory: {case_dir}")
        metrics.append(evaluate_case(case_dir, out_dir, make_plots=not args.check_only))

    if args.write_summary or not args.angle:
        write_study_summary(metrics, out_dir)


if __name__ == "__main__":
    main()

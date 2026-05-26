#!/usr/bin/env python3
"""Lightweight sanity checks for archived two-angle spatial incidence runs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path


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


def iter_ntuple_rows(path: Path):
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(line for line in f if not line.startswith("#"))
        yield from reader


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in iter_ntuple_rows(path))


def read_status(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def read_log_summary(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    patterns = {
        "events": r"# of primary particles:\s+([0-9]+)",
        "scint_created": r"Total number of scintillation photons created:\s+([0-9]+)",
        "op_absorption": r"OpAbsorption:\s+([0-9]+)",
        "sipm_absorption": r"OpAbsorption in SiPM:\s+([0-9]+)",
        "real_seconds": r"Real=([0-9.]+)s",
    }
    out: dict[str, float] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            out[key] = float(match.group(1))
    return out


def choose_bins(n: int) -> int:
    if n <= 0:
        return 128
    return max(128, min(360, round(math.sqrt(n / 25.0))))


def absorption_metrics(path: Path, width_mm: float, length_mm: float) -> dict[str, float]:
    n = 0
    unique_events: set[int] = set()
    x_min = y_min = r_min = math.inf
    x_max = y_max = r_max = -math.inf
    r_sum = 0.0
    outside_x = 0
    outside_y = 0
    rows: list[tuple[float, float]] = []

    if not path.exists():
        return {
            "absorption_rows": 0.0,
            "unique_events_with_absorption": 0.0,
        }

    for row in iter_ntuple_rows(path):
        if len(row) < 3:
            continue
        event_id = int(float(row[0]))
        x = float(row[1])
        y = float(row[2])
        r = math.hypot(x, y)
        n += 1
        unique_events.add(event_id)
        x_min = min(x_min, x)
        x_max = max(x_max, x)
        y_min = min(y_min, y)
        y_max = max(y_max, y)
        r_min = min(r_min, r)
        r_max = max(r_max, r)
        r_sum += r
        outside_x += abs(x) > width_mm / 2.0
        outside_y += abs(y) > length_mm / 2.0
        rows.append((x, y))

    if n == 0:
        return {
            "absorption_rows": 0.0,
            "unique_events_with_absorption": 0.0,
        }

    bins = choose_bins(n)
    x_lo = -width_mm / 2.0
    x_hi = width_mm / 2.0
    y_lo = -length_mm / 2.0
    y_hi = length_mm / 2.0
    grid = [[0 for _ in range(bins)] for _ in range(bins)]
    in_range = 0
    for x, y in rows:
        if not (x_lo <= x <= x_hi and y_lo <= y <= y_hi):
            continue
        ix = min(bins - 1, max(0, int((x - x_lo) / (x_hi - x_lo) * bins)))
        iy = min(bins - 1, max(0, int((y - y_lo) / (y_hi - y_lo) * bins)))
        grid[ix][iy] += 1
        in_range += 1

    positives = [v for col in grid for v in col if v > 0]
    positives_sorted = sorted(positives)
    median_positive = positives_sorted[len(positives_sorted) // 2] if positives_sorted else 0
    max_count = max(positives) if positives else 0
    occupancy = len(positives) / (bins * bins)

    return {
        "absorption_rows": float(n),
        "absorption_rows_in_detector_range": float(in_range),
        "unique_events_with_absorption": float(len(unique_events)),
        "x_min_mm": x_min,
        "x_max_mm": x_max,
        "y_min_mm": y_min,
        "y_max_mm": y_max,
        "r_mean_mm": r_sum / n,
        "r_min_mm": r_min,
        "r_max_mm": r_max,
        "x_outside_detector_fraction": outside_x / n,
        "y_outside_detector_fraction": outside_y / n,
        "heatmap_bins": float(bins),
        "heatmap_occupied_bins": float(len(positives)),
        "heatmap_occupancy_fraction": occupancy,
        "heatmap_max_count": float(max_count),
        "heatmap_median_positive_count": float(median_positive),
        "heatmap_max_to_median_positive": (max_count / median_positive) if median_positive else math.inf,
    }


def sanity_flags(metrics: dict[str, float]) -> list[str]:
    flags: list[str] = []
    if metrics.get("status_code", -1.0) != 0:
        flags.append("simulation status code is nonzero")
    if metrics.get("absorption_rows", 0.0) <= 0:
        flags.append("missing or empty results_nt_absorption.csv")
    if metrics.get("scintillation_rows", 0.0) <= 0:
        flags.append("missing or empty results_nt_scintillation.csv")
    if metrics.get("abs_sp_rows", 0.0) <= 0:
        flags.append("missing or empty results_nt_abs_sp.csv")
    if metrics.get("phot_count_rows", 0.0) <= 0:
        flags.append("missing or empty results_nt_phot_count.csv")
    if metrics.get("events", 0.0) and metrics.get("beam_on", 0.0) and metrics["events"] != metrics["beam_on"]:
        flags.append("event count does not match beam_on")
    if metrics.get("sipm_absorption", 0.0) and metrics.get("absorption_rows", 0.0):
        rel = abs(metrics["sipm_absorption"] - metrics["absorption_rows"]) / max(metrics["sipm_absorption"], 1.0)
        if rel > 0.001:
            flags.append("absorption ntuple rows do not match run-log SiPM absorption count")
    occupancy = metrics.get("heatmap_occupancy_fraction", 0.0)
    if metrics.get("absorption_rows", 0.0) > 0 and occupancy < 0.05:
        flags.append("adaptive heatmap is very sparse")
    if occupancy > 0.98 and metrics.get("heatmap_max_to_median_positive", 0.0) < 2:
        flags.append("adaptive heatmap is almost uniform/full")
    if metrics.get("heatmap_max_to_median_positive", 0.0) > 100 and occupancy < 0.2:
        flags.append("heatmap has isolated hot bins")
    if metrics.get("x_outside_detector_fraction", 0.0) > 0.01:
        flags.append("x hits outside detector exceed 1%")
    if metrics.get("y_outside_detector_fraction", 0.0) > 0.01:
        flags.append("y hits outside detector exceed 1%")
    if metrics.get("unique_events_with_absorption", 0.0) < 50:
        flags.append("few events have measured SiPM photons")
    return flags


def check_case(case_dir: Path) -> dict[str, object]:
    ax, ay = parse_case(case_dir)
    status = read_status(case_dir / "run_status.txt")
    width_mm = float(status.get("detector_width_mm", "51"))
    length_mm = float(status.get("detector_side_length_mm", "51"))

    metrics: dict[str, float] = {
        "angle_x_deg": ax,
        "angle_y_deg": ay,
        "effective_polar_theta_deg": float(status.get("effective_polar_theta_deg", "nan")),
        "effective_azimuth_phi_deg": float(status.get("effective_azimuth_phi_deg", "nan")),
        "beam_on": float(status.get("beam_on", "0") or 0),
        "status_code": float(status.get("status", "-1") or -1),
        "elapsed_seconds": float(status.get("elapsed_seconds", "0") or 0),
        "phot_count_rows": float(count_rows(case_dir / "results_nt_phot_count.csv")),
        "scintillation_rows": float(count_rows(case_dir / "results_nt_scintillation.csv")),
        "abs_sp_rows": float(count_rows(case_dir / "results_nt_abs_sp.csv")),
        "status_rows": float(count_rows(case_dir / "results_nt_status.csv")),
        "pr_int_rows": float(count_rows(case_dir / "results_nt_pr_int.csv")),
        "scat_angle_rows": float(count_rows(case_dir / "results_nt_scat_angles.csv")),
        **read_log_summary(case_dir / "run.log"),
        **absorption_metrics(case_dir / "results_nt_absorption.csv", width_mm, length_mm),
    }
    flags = sanity_flags(metrics)
    return {**metrics, "sanity_flags": flags}


def case_dirs(run_root: Path, ax: str | None, ay: str | None) -> list[Path]:
    if ax is not None or ay is not None:
        if ax is None or ay is None:
            raise ValueError("--ax and --ay must be provided together")
        return [run_root / case_name(ax, ay)]
    return sorted((p for p in run_root.glob("ax_*deg_ay_*deg") if p.is_dir()), key=parse_case)


def write_summary(out_dir: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    keys = [
        "angle_x_deg",
        "angle_y_deg",
        "effective_polar_theta_deg",
        "effective_azimuth_phi_deg",
        "beam_on",
        "elapsed_seconds",
        "real_seconds",
        "scint_created",
        "sipm_absorption",
        "absorption_rows",
        "scintillation_rows",
        "abs_sp_rows",
        "unique_events_with_absorption",
        "heatmap_bins",
        "heatmap_occupancy_fraction",
        "heatmap_max_to_median_positive",
        "r_mean_mm",
        "r_max_mm",
    ]
    with (out_dir / "spatial_angle_sanity_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys + ["sanity_flags"])
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in keys} | {"sanity_flags": "; ".join(row.get("sanity_flags", []))})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--ax")
    parser.add_argument("--ay")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--write-summary", action="store_true")
    args = parser.parse_args()

    run_root = args.run_root.resolve()
    out_dir = (args.out_dir or (run_root / "sanity")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for case_dir in case_dirs(run_root, args.ax, args.ay):
        row = check_case(case_dir)
        rows.append(row)
        ax = row["angle_x_deg"]
        ay = row["angle_y_deg"]
        slug = case_name(ax, ay)
        with (out_dir / f"{slug}_sanity.json").open("w", encoding="utf-8") as f:
            json.dump(row, f, indent=2, sort_keys=True)
        flags = row.get("sanity_flags", [])
        if flags:
            print(f"[sanity] ax={ax:g} ay={ay:g} flags: {'; '.join(flags)}")
        else:
            print(f"[sanity] ax={ax:g} ay={ay:g} ok")

    if args.write_summary or (args.ax is None and args.ay is None):
        write_summary(out_dir, rows)


if __name__ == "__main__":
    main()

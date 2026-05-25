#!/usr/bin/env python3
"""Build a compact heatmap interpolation index from generated heatmap data."""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = REPO_ROOT / "data"
DEFAULT_OUT = DEFAULT_DATA_ROOT / "heatmap_interpolator" / "heatmap_index_360.npz"


@dataclass
class Candidate:
    path: Path
    energy_kev: float
    theta_deg: float
    phi_deg: float
    beam_on: float
    source_bins_x: int
    source_bins_y: int
    case_label: str
    run_label: str
    kind: str
    source_type: str

    @property
    def source_resolution(self) -> int:
        return min(self.source_bins_x, self.source_bins_y)

    @property
    def source_priority(self) -> int:
        if self.source_type == "heatmap_csv" and self.source_resolution >= 360:
            return 3
        if self.source_type == "absorption_ntuple":
            return 2
        if self.source_type == "heatmap_csv":
            return 1
        return 0

    @property
    def key(self) -> tuple[float, float, float]:
        return (round(self.energy_kev, 6), round(self.theta_deg, 6), round(self.phi_deg, 6))


def angle_slug(angle: str | float) -> str:
    text = f"{float(angle):g}" if not isinstance(angle, str) else angle
    return text.replace(".", "p").replace("-", "m")


def read_status(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def infer_edges(centers: np.ndarray) -> np.ndarray:
    if len(centers) == 0:
        return np.asarray([], dtype=np.float64)
    if len(centers) == 1:
        return np.asarray([centers[0] - 0.5, centers[0] + 0.5], dtype=np.float64)
    mids = 0.5 * (centers[:-1] + centers[1:])
    first = centers[0] - (mids[0] - centers[0])
    last = centers[-1] + (centers[-1] - mids[-1])
    return np.concatenate([[first], mids, [last]]).astype(np.float64)


def target_centers(detector_mm: float, bins: int) -> np.ndarray:
    step = detector_mm / bins
    return np.linspace(-detector_mm / 2.0 + step / 2.0, detector_mm / 2.0 - step / 2.0, bins)


def read_heatmap_csv(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows: list[tuple[float, float, float]] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append((float(row["x_mm"]), float(row["y_mm"]), float(row["count"])))

    x_centers = np.asarray(sorted({x for x, _, _ in rows}), dtype=np.float64)
    y_centers = np.asarray(sorted({y for _, y, _ in rows}), dtype=np.float64)
    hist = np.zeros((len(x_centers), len(y_centers)), dtype=np.float64)
    x_index = {x: i for i, x in enumerate(x_centers)}
    y_index = {y: i for i, y in enumerate(y_centers)}
    for x, y, count in rows:
        hist[x_index[x], y_index[y]] = count
    return x_centers, y_centers, hist


def read_absorption_ntuple_heatmap(
    path: Path,
    bins: int,
    detector_mm: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    points = np.loadtxt(
        path,
        delimiter=",",
        comments="#",
        usecols=(1, 2),
        dtype=np.float32,
    )
    if points.size == 0:
        hist = np.zeros((bins, bins), dtype=np.float64)
    else:
        if points.ndim == 1:
            points = points.reshape(1, 2)
        hist, _, _ = np.histogram2d(
            points[:, 0],
            points[:, 1],
            bins=bins,
            range=[[-detector_mm / 2.0, detector_mm / 2.0], [-detector_mm / 2.0, detector_mm / 2.0]],
        )
    centers = target_centers(detector_mm, bins)
    return centers, centers, hist


def density_from_counts(
    counts: np.ndarray,
    x_centers: np.ndarray,
    y_centers: np.ndarray,
    beam_on: float,
) -> np.ndarray:
    x_edges = infer_edges(x_centers)
    y_edges = infer_edges(y_centers)
    x_width_cm = np.diff(x_edges) / 10.0
    y_width_cm = np.diff(y_edges) / 10.0
    area_cm2 = np.outer(x_width_cm, y_width_cm)
    return counts / np.maximum(beam_on * area_cm2, 1e-12)


def resample_grid(
    grid: np.ndarray,
    src_x: np.ndarray,
    src_y: np.ndarray,
    dst_x: np.ndarray,
    dst_y: np.ndarray,
) -> np.ndarray:
    x_pass = np.empty((len(dst_x), grid.shape[1]), dtype=np.float64)
    for iy in range(grid.shape[1]):
        x_pass[:, iy] = np.interp(dst_x, src_x, grid[:, iy])
    out = np.empty((len(dst_x), len(dst_y)), dtype=np.float64)
    for ix in range(len(dst_x)):
        out[ix, :] = np.interp(dst_y, src_y, x_pass[ix, :])
    return out


def candidate_from_path(path: Path) -> Candidate | None:
    if path.parent.name != "plots":
        return None

    run_root = path.parent.parent
    run_label = run_root.name

    spatial = re.match(r"ax_([0-9pm.-]+)deg_ay_([0-9pm.-]+)deg_heatmap(?:_lowres)?_([0-9]+)x([0-9]+)\.csv$", path.name)
    if spatial:
        ax = float(spatial.group(1).replace("p", ".").replace("m", "-"))
        ay = float(spatial.group(2).replace("p", ".").replace("m", "-"))
        case_label = f"ax_{angle_slug(ax)}deg_ay_{angle_slug(ay)}deg"
        status = read_status(run_root / case_label / "run_status.txt")
        return Candidate(
            path=path,
            energy_kev=float(status.get("energy_keV", "nan")),
            theta_deg=float(status.get("effective_polar_theta_deg", "nan")),
            phi_deg=float(status.get("effective_azimuth_phi_deg", "nan")),
            beam_on=float(status.get("beam_on", "1") or 1),
            source_bins_x=int(spatial.group(3)),
            source_bins_y=int(spatial.group(4)),
            case_label=case_label,
            run_label=run_label,
            kind="spatial",
            source_type="heatmap_csv",
        )

    incidence = re.match(r"angle_([0-9pm.-]+)deg_heatmap(?:_lowres)?_([0-9]+)x([0-9]+)\.csv$", path.name)
    if incidence:
        theta = float(incidence.group(1).replace("p", ".").replace("m", "-"))
        case_label = f"angle_{angle_slug(theta)}deg"
        status = read_status(run_root / case_label / "run_status.txt")
        return Candidate(
            path=path,
            energy_kev=float(status.get("energy_keV", "nan")),
            theta_deg=theta,
            phi_deg=0.0,
            beam_on=float(status.get("beam_on", "1") or 1),
            source_bins_x=int(incidence.group(2)),
            source_bins_y=int(incidence.group(3)),
            case_label=case_label,
            run_label=run_label,
            kind="incidence",
            source_type="heatmap_csv",
        )

    return None


def candidate_from_absorption_path(path: Path, target_bins: int) -> Candidate | None:
    if path.name != "results_nt_absorption.csv":
        return None

    case_dir = path.parent
    run_root = case_dir.parent
    run_label = run_root.name
    status = read_status(case_dir / "run_status.txt")
    if status.get("status") not in (None, "0"):
        return None

    spatial = re.match(r"ax_([0-9pm.-]+)deg_ay_([0-9pm.-]+)deg$", case_dir.name)
    if spatial:
        return Candidate(
            path=path,
            energy_kev=float(status.get("energy_keV", "nan")),
            theta_deg=float(status.get("effective_polar_theta_deg", "nan")),
            phi_deg=float(status.get("effective_azimuth_phi_deg", "nan")),
            beam_on=float(status.get("beam_on", "1") or 1),
            source_bins_x=target_bins,
            source_bins_y=target_bins,
            case_label=case_dir.name,
            run_label=run_label,
            kind="spatial",
            source_type="absorption_ntuple",
        )

    incidence = re.match(r"angle_([0-9pm.-]+)deg$", case_dir.name)
    if incidence:
        theta = float(incidence.group(1).replace("p", ".").replace("m", "-"))
        return Candidate(
            path=path,
            energy_kev=float(status.get("energy_keV", "nan")),
            theta_deg=theta,
            phi_deg=0.0,
            beam_on=float(status.get("beam_on", "1") or 1),
            source_bins_x=target_bins,
            source_bins_y=target_bins,
            case_label=case_dir.name,
            run_label=run_label,
            kind="incidence",
            source_type="absorption_ntuple",
        )

    return None


def discover_candidates(data_root: Path, target_bins: int) -> tuple[list[Candidate], list[Candidate]]:
    grouped: dict[tuple[float, float, float], list[Candidate]] = {}
    for path in sorted(data_root.rglob("*heatmap*.csv")):
        candidate = candidate_from_path(path)
        if candidate is None:
            continue
        values = [candidate.energy_kev, candidate.theta_deg, candidate.phi_deg, candidate.beam_on]
        if any(not np.isfinite(v) for v in values) or candidate.beam_on <= 0:
            continue
        grouped.setdefault(candidate.key, []).append(candidate)

    for path in sorted(data_root.rglob("results_nt_absorption.csv")):
        candidate = candidate_from_absorption_path(path, target_bins)
        if candidate is None:
            continue
        values = [candidate.energy_kev, candidate.theta_deg, candidate.phi_deg, candidate.beam_on]
        if any(not np.isfinite(v) for v in values) or candidate.beam_on <= 0:
            continue
        grouped.setdefault(candidate.key, []).append(candidate)

    selected: list[Candidate] = []
    duplicates: list[Candidate] = []
    for items in grouped.values():
        ranked = sorted(items, key=lambda c: (c.source_resolution, c.source_priority, c.path.name), reverse=True)
        selected.append(ranked[0])
        duplicates.extend(ranked[1:])
    selected.sort(key=lambda c: (c.energy_kev, c.theta_deg, c.phi_deg, c.case_label))
    duplicates.sort(key=lambda c: str(c.path))
    return selected, duplicates


def build_index(data_root: Path, out_path: Path, target_bins: int = 360, detector_mm: float = 51.0) -> dict[str, object]:
    selected, duplicates = discover_candidates(data_root, target_bins)
    if not selected:
        raise RuntimeError(f"No generated heatmap data found under {data_root}")

    dst_x = target_centers(detector_mm, target_bins)
    dst_y = target_centers(detector_mm, target_bins)
    heatmaps: list[np.ndarray] = []
    samples: list[dict[str, object]] = []

    for item in selected:
        if item.source_type == "absorption_ntuple":
            x_centers, y_centers, counts = read_absorption_ntuple_heatmap(item.path, target_bins, detector_mm)
        else:
            x_centers, y_centers, counts = read_heatmap_csv(item.path)
        density = density_from_counts(counts, x_centers, y_centers, item.beam_on)
        density_360 = resample_grid(density, x_centers, y_centers, dst_x, dst_y)
        heatmaps.append(density_360.astype(np.float32))
        samples.append(
            {
                "energy_kev": item.energy_kev,
                "theta_deg": item.theta_deg,
                "phi_deg": item.phi_deg,
                "beam_on": item.beam_on,
                "source_bins": [item.source_bins_x, item.source_bins_y],
                "case_label": item.case_label,
                "run_label": item.run_label,
                "kind": item.kind,
                "source_type": item.source_type,
                "source_path": str(item.path.relative_to(REPO_ROOT)),
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out_path,
        heatmaps=np.stack(heatmaps, axis=0).astype(np.float32),
        energies=np.asarray([s["energy_kev"] for s in samples], dtype=np.float32),
        thetas=np.asarray([s["theta_deg"] for s in samples], dtype=np.float32),
        phis=np.asarray([s["phi_deg"] for s in samples], dtype=np.float32),
        x_centers_mm=dst_x.astype(np.float32),
        y_centers_mm=dst_y.astype(np.float32),
    )

    metadata = {
        "target_bins": target_bins,
        "detector_mm": detector_mm,
        "quantity": "density_counts_per_gamma_cm2",
        "sample_count": len(samples),
        "duplicate_heatmap_files_ignored": len(duplicates),
        "source_preference": [
            "360x360 heatmap CSV",
            "360x360 histogram rebuilt from results_nt_absorption.csv",
            "lower-resolution heatmap CSV fallback",
        ],
        "samples": samples,
        "duplicates": [
            {
                "energy_kev": d.energy_kev,
                "theta_deg": d.theta_deg,
                "phi_deg": d.phi_deg,
                "source_bins": [d.source_bins_x, d.source_bins_y],
                "source_type": d.source_type,
                "source_path": str(d.path.relative_to(REPO_ROOT)),
            }
            for d in duplicates
        ],
    }
    out_path.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--target-bins", type=int, default=360)
    parser.add_argument("--detector-mm", type=float, default=51.0)
    args = parser.parse_args()

    metadata = build_index(args.data_root.resolve(), args.out.resolve(), args.target_bins, args.detector_mm)
    print(f"wrote {args.out}")
    print(f"samples={metadata['sample_count']} duplicate_heatmap_files_ignored={metadata['duplicate_heatmap_files_ignored']}")


if __name__ == "__main__":
    main()

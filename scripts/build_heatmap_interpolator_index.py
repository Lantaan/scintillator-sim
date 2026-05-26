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
from scipy import ndimage


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


def block_mean(image: np.ndarray, bins: int) -> np.ndarray:
    if image.shape[0] == bins and image.shape[1] == bins:
        return image.astype(np.float32, copy=False)
    if image.shape[0] % bins == 0 and image.shape[1] % bins == 0:
        fx = image.shape[0] // bins
        fy = image.shape[1] // bins
        return image.reshape(bins, fx, bins, fy).mean(axis=(1, 3)).astype(np.float32)
    zoom = (bins / image.shape[0], bins / image.shape[1])
    return ndimage.zoom(image, zoom, order=1).astype(np.float32)


def flow_input_image(density: np.ndarray, flow_bins: int) -> np.ndarray:
    image = np.log1p(np.maximum(density, 0.0))
    lo, hi = np.percentile(image, [1.0, 99.5])
    image = np.clip(image, lo, hi)
    if hi > lo:
        image = (image - lo) / (hi - lo)
    else:
        image = np.zeros_like(image)
    image = ndimage.gaussian_filter(image.astype(np.float32), sigma=1.0)
    image = block_mean(image, flow_bins)
    return ndimage.gaussian_filter(image, sigma=0.6).astype(np.float32)


def horn_schunck_flow(
    source: np.ndarray,
    target: np.ndarray,
    alpha: float = 0.8,
    iterations: int = 100,
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate dense source->target flow in low-resolution pixel units."""
    source = source.astype(np.float32, copy=False)
    target = target.astype(np.float32, copy=False)
    average = 0.5 * (source + target)
    ix = ndimage.sobel(average, axis=0, mode="nearest") / 8.0
    iy = ndimage.sobel(average, axis=1, mode="nearest") / 8.0
    it = target - source
    denom = alpha * alpha + ix * ix + iy * iy
    kernel = np.asarray(
        [
            [1.0 / 12.0, 1.0 / 6.0, 1.0 / 12.0],
            [1.0 / 6.0, 0.0, 1.0 / 6.0],
            [1.0 / 12.0, 1.0 / 6.0, 1.0 / 12.0],
        ],
        dtype=np.float32,
    )
    dx = np.zeros_like(source, dtype=np.float32)
    dy = np.zeros_like(source, dtype=np.float32)
    for _ in range(iterations):
        dx_avg = ndimage.convolve(dx, kernel, mode="nearest")
        dy_avg = ndimage.convolve(dy, kernel, mode="nearest")
        step = (ix * dx_avg + iy * dy_avg + it) / denom
        dx = dx_avg - ix * step
        dy = dy_avg - iy * step
    return dx.astype(np.float32), dy.astype(np.float32)


def build_flow_fields(flow_images: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    count = len(flow_images)
    bins = flow_images[0].shape[0] if flow_images else 0
    flow_x = np.zeros((count, count, bins, bins), dtype=np.float32)
    flow_y = np.zeros((count, count, bins, bins), dtype=np.float32)
    for i, source in enumerate(flow_images):
        for j, target in enumerate(flow_images):
            if i == j:
                continue
            flow_x[i, j], flow_y[i, j] = horn_schunck_flow(source, target)
    return flow_x, flow_y


def ot_input_image(density: np.ndarray, ot_bins: int) -> np.ndarray:
    """Prepare a normalized, denoised density field for approximate OT."""
    image = np.maximum(density.astype(np.float32, copy=False), 0.0)
    image = ndimage.gaussian_filter(image, sigma=1.2)
    image = block_mean(image, ot_bins)
    image = ndimage.gaussian_filter(image, sigma=0.7)
    hi = np.percentile(image, 99.7)
    if hi > 0:
        image = np.clip(image, 0.0, hi)
    image = np.maximum(image, 0.0) + 1e-8
    image /= np.sum(image)
    return image.astype(np.float32)


def make_ot_kernel(bins: int, epsilon: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    axis = np.linspace(0.0, 1.0, bins, dtype=np.float32)
    gx, gy = np.meshgrid(axis, axis, indexing="ij")
    coords_x = gx.ravel()
    coords_y = gy.ravel()
    dx = coords_x[:, None] - coords_x[None, :]
    dy = coords_y[:, None] - coords_y[None, :]
    cost = dx * dx + dy * dy
    kernel = np.exp(-cost / epsilon).astype(np.float32)
    return kernel, coords_x.astype(np.float32), coords_y.astype(np.float32)


def sinkhorn_barycentric_flow(
    source: np.ndarray,
    target: np.ndarray,
    kernel: np.ndarray,
    coords_x: np.ndarray,
    coords_y: np.ndarray,
    iterations: int,
) -> tuple[np.ndarray, np.ndarray]:
    bins = source.shape[0]
    p = source.ravel().astype(np.float32)
    q = target.ravel().astype(np.float32)
    tiny = np.float32(1e-12)
    u = np.ones_like(p, dtype=np.float32)
    v = np.ones_like(q, dtype=np.float32)
    for _ in range(iterations):
        u = p / np.maximum(kernel @ v, tiny)
        v = q / np.maximum(kernel.T @ u, tiny)

    denom = np.maximum(kernel @ v, tiny)
    mapped_x = (kernel @ (v * coords_x)) / denom
    mapped_y = (kernel @ (v * coords_y)) / denom
    dx = (mapped_x - coords_x).reshape(bins, bins) * (bins - 1)
    dy = (mapped_y - coords_y).reshape(bins, bins) * (bins - 1)
    return dx.astype(np.float32), dy.astype(np.float32)


def build_ot_fields(
    ot_images: list[np.ndarray],
    epsilon: float,
    iterations: int,
) -> tuple[np.ndarray, np.ndarray]:
    count = len(ot_images)
    bins = ot_images[0].shape[0] if ot_images else 0
    kernel, coords_x, coords_y = make_ot_kernel(bins, epsilon)
    ot_x = np.zeros((count, count, bins, bins), dtype=np.float32)
    ot_y = np.zeros((count, count, bins, bins), dtype=np.float32)
    for i, source in enumerate(ot_images):
        for j, target in enumerate(ot_images):
            if i == j:
                continue
            ot_x[i, j], ot_y[i, j] = sinkhorn_barycentric_flow(
                source,
                target,
                kernel,
                coords_x,
                coords_y,
                iterations,
            )
    return ot_x, ot_y


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


def build_index(
    data_root: Path,
    out_path: Path,
    target_bins: int = 360,
    detector_mm: float = 51.0,
    flow_bins: int = 90,
    ot_bins: int = 48,
    ot_epsilon: float = 0.035,
    ot_iterations: int = 80,
    skip_flow: bool = False,
    skip_ot: bool = False,
) -> dict[str, object]:
    selected, duplicates = discover_candidates(data_root, target_bins)
    if not selected:
        raise RuntimeError(f"No generated heatmap data found under {data_root}")

    dst_x = target_centers(detector_mm, target_bins)
    dst_y = target_centers(detector_mm, target_bins)
    heatmaps: list[np.ndarray] = []
    flow_images: list[np.ndarray] = []
    ot_images: list[np.ndarray] = []
    samples: list[dict[str, object]] = []

    for item in selected:
        if item.source_type == "absorption_ntuple":
            x_centers, y_centers, counts = read_absorption_ntuple_heatmap(item.path, target_bins, detector_mm)
        else:
            x_centers, y_centers, counts = read_heatmap_csv(item.path)
        density = density_from_counts(counts, x_centers, y_centers, item.beam_on)
        density_360 = resample_grid(density, x_centers, y_centers, dst_x, dst_y)
        heatmaps.append(density_360.astype(np.float32))
        flow_images.append(flow_input_image(density_360, flow_bins))
        ot_images.append(ot_input_image(density_360, ot_bins))
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
    arrays: dict[str, np.ndarray] = {
        "heatmaps": np.stack(heatmaps, axis=0).astype(np.float32),
        "energies": np.asarray([s["energy_kev"] for s in samples], dtype=np.float32),
        "thetas": np.asarray([s["theta_deg"] for s in samples], dtype=np.float32),
        "phis": np.asarray([s["phi_deg"] for s in samples], dtype=np.float32),
        "x_centers_mm": dst_x.astype(np.float32),
        "y_centers_mm": dst_y.astype(np.float32),
    }

    has_flow = False
    if not skip_flow:
        flow_x, flow_y = build_flow_fields(flow_images)
        arrays["flow_x"] = flow_x
        arrays["flow_y"] = flow_y
        arrays["flow_bins"] = np.asarray([flow_bins], dtype=np.int32)
        has_flow = True

    has_ot = False
    if not skip_ot:
        ot_x, ot_y = build_ot_fields(ot_images, ot_epsilon, ot_iterations)
        arrays["ot_x"] = ot_x
        arrays["ot_y"] = ot_y
        arrays["ot_bins"] = np.asarray([ot_bins], dtype=np.int32)
        has_ot = True

    np.savez_compressed(out_path, **arrays)

    metadata = {
        "target_bins": target_bins,
        "flow_bins": flow_bins if has_flow else 0,
        "has_flow_fields": has_flow,
        "flow_method": "Horn-Schunck dense flow on smoothed log-density heatmaps" if has_flow else "none",
        "ot_bins": ot_bins if has_ot else 0,
        "has_ot_fields": has_ot,
        "ot_method": (
            f"Entropic Sinkhorn barycentric transport maps on {ot_bins}x{ot_bins} clipped/smoothed density"
            if has_ot
            else "none"
        ),
        "ot_epsilon": ot_epsilon if has_ot else 0.0,
        "ot_iterations": ot_iterations if has_ot else 0,
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
    parser.add_argument("--flow-bins", type=int, default=90)
    parser.add_argument("--ot-bins", type=int, default=48)
    parser.add_argument("--ot-epsilon", type=float, default=0.035)
    parser.add_argument("--ot-iterations", type=int, default=80)
    parser.add_argument("--skip-flow", action="store_true")
    parser.add_argument("--skip-ot", action="store_true")
    args = parser.parse_args()

    metadata = build_index(
        args.data_root.resolve(),
        args.out.resolve(),
        args.target_bins,
        args.detector_mm,
        args.flow_bins,
        args.ot_bins,
        args.ot_epsilon,
        args.ot_iterations,
        args.skip_flow,
        args.skip_ot,
    )
    print(f"wrote {args.out}")
    print(f"samples={metadata['sample_count']} duplicate_heatmap_files_ignored={metadata['duplicate_heatmap_files_ignored']}")


if __name__ == "__main__":
    main()

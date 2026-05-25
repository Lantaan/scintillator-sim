#!/usr/bin/env python3
"""Serve a fast local UI for interpolating archived scintillation heatmaps."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
STATIC_DIR = REPO_ROOT / "tools" / "heatmap_interpolator" / "static"
DEFAULT_INDEX = REPO_ROOT / "data" / "heatmap_interpolator" / "heatmap_index_360.npz"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_heatmap_interpolator_index import build_index  # noqa: E402


class HeatmapStore:
    def __init__(
        self,
        index_path: Path,
        energy_scale: float | None = None,
        theta_scale: float = 90.0,
        phi_scale: float = 90.0,
    ) -> None:
        self.index_path = index_path
        bundle = np.load(index_path)
        self.heatmaps = np.asarray(bundle["heatmaps"], dtype=np.float32)
        self.energies = np.asarray(bundle["energies"], dtype=np.float32)
        self.thetas = np.asarray(bundle["thetas"], dtype=np.float32)
        self.phis = np.asarray(bundle["phis"], dtype=np.float32)
        self.x_centers_mm = np.asarray(bundle["x_centers_mm"], dtype=np.float32)
        self.y_centers_mm = np.asarray(bundle["y_centers_mm"], dtype=np.float32)
        self.metadata = json.loads(index_path.with_suffix(".json").read_text(encoding="utf-8"))

        energy_span = float(np.max(self.energies) - np.min(self.energies)) if len(self.energies) else 1.0
        self.energy_scale = float(energy_scale or max(100.0, energy_span))
        self.theta_scale = float(theta_scale)
        self.phi_scale = float(phi_scale)

    def _distances(self, energy: float, theta: float, phi: float) -> np.ndarray:
        d_energy = (self.energies - energy) / self.energy_scale
        d_theta = (self.thetas - theta) / self.theta_scale
        d_phi_raw = np.abs(self.phis - phi)
        d_phi = np.minimum(d_phi_raw, 360.0 - d_phi_raw) / self.phi_scale
        return np.sqrt(d_energy * d_energy + d_theta * d_theta + d_phi * d_phi)

    def interpolate(self, energy: float, theta: float, phi: float, k: int = 4, power: float = 2.0) -> tuple[np.ndarray, dict[str, object]]:
        start = time.perf_counter()
        distances = self._distances(energy, theta, phi)
        nearest = np.argsort(distances)[: max(1, min(k, len(distances)))]
        exact = bool(distances[nearest[0]] < 1e-7)

        if exact:
            weights = np.asarray([1.0], dtype=np.float32)
            used = nearest[:1]
            image = self.heatmaps[used[0]]
        else:
            used = nearest
            local_distances = np.maximum(distances[used], 1e-9)
            weights64 = 1.0 / np.power(local_distances, power)
            weights64 /= np.sum(weights64)
            weights = weights64.astype(np.float32)
            image = np.tensordot(weights, self.heatmaps[used], axes=(0, 0)).astype(np.float32, copy=False)

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        contributors = []
        samples = self.metadata["samples"]
        for idx, weight in zip(used, weights):
            sample = samples[int(idx)]
            contributors.append(
                {
                    "case_label": sample["case_label"],
                    "energy_kev": float(sample["energy_kev"]),
                    "theta_deg": float(sample["theta_deg"]),
                    "phi_deg": float(sample["phi_deg"]),
                    "weight": float(weight),
                    "distance": float(distances[idx]),
                    "source_bins": sample["source_bins"],
                    "source_type": sample.get("source_type", "unknown"),
                    "source_path": sample.get("source_path", ""),
                }
            )

        details = {
            "interpolation_ms": elapsed_ms,
            "exact": exact,
            "contributors": contributors,
            "shape": list(image.shape),
            "quantity": self.metadata.get("quantity", "density_counts_per_gamma_cm2"),
            "energy_scale": self.energy_scale,
            "theta_scale": self.theta_scale,
            "phi_scale": self.phi_scale,
        }
        return image, details

    def benchmark(self, energy: float, theta: float, phi: float, k: int, repeats: int) -> dict[str, object]:
        timings = []
        for _ in range(max(1, repeats)):
            _, details = self.interpolate(energy, theta, phi, k)
            timings.append(float(details["interpolation_ms"]))
        values = np.asarray(timings, dtype=np.float64)
        return {
            "repeats": int(len(values)),
            "mean_ms": float(np.mean(values)),
            "median_ms": float(np.median(values)),
            "p95_ms": float(np.percentile(values, 95)),
            "min_ms": float(np.min(values)),
            "max_ms": float(np.max(values)),
        }


def make_handler(store: HeatmapStore):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

        def log_message(self, format: str, *args) -> None:
            sys.stderr.write("[heatmap-ui] " + (format % args) + "\n")

        def send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_text(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
            body = message.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def parse_float(self, query: dict[str, list[str]], name: str, default: float) -> float:
            try:
                return float(query.get(name, [str(default)])[0])
            except ValueError as exc:
                raise ValueError(f"{name} must be numeric") from exc

        def parse_int(self, query: dict[str, list[str]], name: str, default: int, low: int, high: int) -> int:
            try:
                value = int(float(query.get(name, [str(default)])[0]))
            except ValueError as exc:
                raise ValueError(f"{name} must be numeric") from exc
            return max(low, min(high, value))

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)

            if parsed.path == "/api/metadata":
                payload = dict(store.metadata)
                payload.update(
                    {
                        "index_path": str(store.index_path),
                        "energy_scale": store.energy_scale,
                        "theta_scale": store.theta_scale,
                        "phi_scale": store.phi_scale,
                    }
                )
                self.send_json(payload)
                return

            if parsed.path == "/api/benchmark":
                try:
                    energy = self.parse_float(query, "energy", 662.0)
                    theta = self.parse_float(query, "theta", 45.0)
                    phi = self.parse_float(query, "phi", 0.0)
                    k = self.parse_int(query, "k", 4, 1, 12)
                    repeats = self.parse_int(query, "repeat", 100, 1, 10000)
                    self.send_json(store.benchmark(energy, theta, phi, k, repeats))
                except ValueError as exc:
                    self.send_text(str(exc))
                return

            if parsed.path == "/api/interpolate":
                try:
                    energy = self.parse_float(query, "energy", 662.0)
                    theta = self.parse_float(query, "theta", 45.0)
                    phi = self.parse_float(query, "phi", 0.0)
                    k = self.parse_int(query, "k", 4, 1, 12)
                    if not all(math.isfinite(v) for v in [energy, theta, phi]):
                        raise ValueError("energy, theta, and phi must be finite")
                    image, details = store.interpolate(energy, theta, phi, k)
                    body = np.ascontiguousarray(image, dtype=np.float32).tobytes()
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("X-Shape", f"{image.shape[0]}x{image.shape[1]}")
                    self.send_header("X-Interp-Ms", f"{details['interpolation_ms']:.6f}")
                    self.send_header("X-Exact-Match", "1" if details["exact"] else "0")
                    self.send_header("X-Quantity", str(details["quantity"]))
                    self.send_header("X-Contributors", json.dumps(details["contributors"], separators=(",", ":")))
                    self.end_headers()
                    self.wfile.write(body)
                except ValueError as exc:
                    self.send_text(str(exc))
                return

            if parsed.path == "/":
                self.path = "/index.html"
            super().do_GET()

    return Handler


def ensure_index(index_path: Path, rebuild: bool) -> None:
    if rebuild or not index_path.exists() or not index_path.with_suffix(".json").exists():
        build_index(REPO_ROOT / "data", index_path, target_bins=360, detector_mm=51.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--energy-scale", type=float)
    parser.add_argument("--theta-scale", type=float, default=90.0)
    parser.add_argument("--phi-scale", type=float, default=90.0)
    args = parser.parse_args()

    index_path = args.index.resolve()
    ensure_index(index_path, args.rebuild_index)
    store = HeatmapStore(index_path, args.energy_scale, args.theta_scale, args.phi_scale)

    server = ThreadingHTTPServer((args.host, args.port), make_handler(store))
    url = f"http://{args.host}:{args.port}"
    print(f"Heatmap interpolator UI: {url}")
    print(f"Loaded {store.heatmaps.shape[0]} heatmaps at {store.heatmaps.shape[1]}x{store.heatmaps.shape[2]}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

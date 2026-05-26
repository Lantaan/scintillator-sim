#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = REPO_ROOT / "data" / "fig310_runs"
OUT_PNG = REPO_ROOT / "data" / "fig310_xaxis_distribution.png"


def load_x_from_absorption_ntuple(path: Path) -> np.ndarray:
    xs = []
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        for row in r:
            if not row:
                continue
            if row[0].startswith("#") or row[0] == "eventID":
                continue
            try:
                xs.append(float(row[1]))  # x column in mm
            except (IndexError, ValueError):
                continue
    return np.asarray(xs, dtype=float)


def normalized_curve(energy_kev: int) -> tuple[np.ndarray, np.ndarray]:
    p = RUN_ROOT / f"{energy_kev}keV" / "results_nt_absorption.csv"
    xs = load_x_from_absorption_ntuple(p)
    bins = 51
    xmin, xmax = -25.5, 25.5
    y, edges = np.histogram(xs, bins=bins, range=(xmin, xmax), density=False)
    x = 0.5 * (edges[:-1] + edges[1:])
    s = y.sum()
    y = y / s if s > 0 else y
    return x, y


def mean_group(energies: list[int]) -> tuple[np.ndarray, np.ndarray]:
    curves = [normalized_curve(e) for e in energies]
    x0 = curves[0][0]
    ys = []
    for x, y in curves:
        if x.shape != x0.shape or np.max(np.abs(x - x0)) > 1e-9:
            y = np.interp(x0, x, y, left=0, right=0)
        ys.append(y)
    y_mean = np.mean(np.vstack(ys), axis=0)
    return x0, y_mean


def main() -> None:
    x_20_50, y_20_50 = mean_group([20, 50])
    x_100, y_100 = mean_group([100])
    x_200, y_200 = mean_group([200])
    x_500_4000, y_500_4000 = mean_group([500, 1000, 2000, 4000])

    fig, ax = plt.subplots(figsize=(7.0, 5.2), dpi=160)
    ax.plot(x_20_50, y_20_50, lw=2, label="20 - 50 keV")
    ax.plot(x_100, y_100, lw=2, label="100 keV")
    ax.plot(x_200, y_200, lw=2, label="200 keV")
    ax.plot(x_500_4000, y_500_4000, lw=2, label="500 - 4000 keV")
    ax.set_xlabel("x, mm")
    ax.set_ylabel("Frequency distribution along x-axis")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT_PNG)
    plt.close(fig)
    print(f"Wrote plot: {OUT_PNG}")


if __name__ == "__main__":
    main()

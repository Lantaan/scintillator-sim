#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = REPO_ROOT / "data" / "fig36_photopeak_runs"
OUT_PNG = REPO_ROOT / "data" / "fig36_photopeak_efficiency.png"
OUT_CSV = REPO_ROOT / "data" / "fig36_photopeak_efficiency_summary.csv"
ENERGIES_KEV = [20, 50, 100, 200, 500, 1000, 4000]


def load_counts(csv_path: Path) -> np.ndarray:
    vals = []
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        for row in r:
            if not row or row[0].startswith("#"):
                continue
            if row[0] == "eventID":
                continue
            vals.append(float(row[1]))
    return np.asarray(vals, dtype=float)


def fit_photopeak_window(counts: np.ndarray, energy_kev: float) -> tuple[float, float]:
    # Fit a Gaussian-like full-energy peak near expected light yield.
    expected = 60.0 * energy_kev
    bins = min(180, max(60, int(np.sqrt(counts.size) * 3)))
    hist, edges = np.histogram(counts, bins=bins)
    centers = 0.5 * (edges[:-1] + edges[1:])

    # Strict ROI around full-energy expectation to avoid fitting Compton continuum.
    mask_roi = (centers >= 0.90 * expected) & (centers <= 1.05 * expected)
    if not np.any(mask_roi):
        return 0.97 * expected, 1.03 * expected

    roi_idx = np.where(mask_roi)[0]
    if roi_idx.size == 0:
        return 0.97 * expected, 1.03 * expected

    peak_idx = roi_idx[np.argmax(hist[roi_idx])]
    peak_h = hist[peak_idx]
    if peak_h <= 0:
        return 0.97 * expected, 1.03 * expected

    # Collect bins around the peak with sufficient population for log-fit.
    fit_sel = (hist > 0) & (hist >= max(2, 0.10 * peak_h))
    fit_sel &= (centers >= 0.90 * expected)
    fit_sel &= (centers <= 1.05 * expected)

    x = centers[fit_sel]
    y = hist[fit_sel]
    if x.size < 5:
        # Fallback: ±3% true symmetric window around expected yield.
        return 0.97 * expected, 1.03 * expected

    # log(y) = a x^2 + b x + c for a Gaussian-like peak.
    coeff = np.polyfit(x, np.log(y), 2)
    a, b, _ = coeff
    if a >= 0:
        return 0.97 * expected, 1.03 * expected

    mu = -b / (2.0 * a)
    sigma = np.sqrt(-1.0 / (2.0 * a))
    if not np.isfinite(mu) or not np.isfinite(sigma) or sigma <= 0:
        return 0.97 * expected, 1.03 * expected

    fwhm = 2.355 * sigma
    lo = mu - 0.5 * fwhm
    hi = mu + 0.5 * fwhm
    # Keep bounds anchored to full-energy neighborhood.
    lo = max(lo, 0.90 * expected)
    hi = min(hi, 1.05 * expected)
    return max(0.0, lo), hi


def compute_series(cfg: str) -> list[float]:
    out = []
    for e in ENERGIES_KEV:
        src = RUN_ROOT / cfg / f"{e}keV" / "results_nt_phot_count.csv"
        counts = load_counts(src)
        if counts.size == 0:
            out.append(0.0)
            continue
        lo, hi = fit_photopeak_window(counts, e)
        nph = np.count_nonzero((counts >= lo) & (counts <= hi))
        nc = counts.size
        out.append(100.0 * nph / nc)
    return out


def main() -> None:
    bare = compute_series("bare")
    refla = compute_series("reflA")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["energy_keV", "bare_photopeak_eff_percent", "reflectorA_photopeak_eff_percent"])
        for e, b, r in zip(ENERGIES_KEV, bare, refla):
            w.writerow([e, f"{b:.6f}", f"{r:.6f}"])

    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)
    ax.plot(ENERGIES_KEV, bare, marker="o", lw=2, label="51 x 51 x 10, without reflector")
    ax.plot(ENERGIES_KEV, refla, marker="s", lw=2, label="51 x 51 x 10, reflector A")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xticks(ENERGIES_KEV, labels=[str(e) for e in ENERGIES_KEV])
    ax.set_xlabel("energy, keV")
    ax.set_ylabel("Photo-peak efficiency, %")
    ax.set_ylim(1, 100)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_PNG)
    plt.close(fig)
    print(f"Wrote plot: {OUT_PNG}")
    print(f"Wrote summary: {OUT_CSV}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = REPO_ROOT / "data" / "fig36_runs"
OUT_PNG = REPO_ROOT / "data" / "fig36_light_output_vs_energy.png"
OUT_CSV = REPO_ROOT / "data" / "fig36_light_output_vs_energy_summary.csv"
ENERGIES_KEV = [20, 50, 100, 200, 500, 1000, 4000]

RE_N_PRIMARY = re.compile(r"# of primary particles:\s+(\d+)")
RE_SIPM_ABS = re.compile(r"OpAbsorption in SiPM:\s+(\d+)")


def parse_log(log_path: Path) -> tuple[int, int]:
    n_primary = None
    sipm_abs = None
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        m = RE_N_PRIMARY.search(line)
        if m:
            n_primary = int(m.group(1))
        m = RE_SIPM_ABS.search(line)
        if m:
            sipm_abs = int(m.group(1))
    if n_primary is None or sipm_abs is None:
        raise RuntimeError(f"Could not parse required metrics from {log_path}")
    return n_primary, sipm_abs


def compute_series(cfg: str) -> list[float]:
    values: list[float] = []
    for e in ENERGIES_KEV:
        log_path = RUN_ROOT / cfg / f"{e}keV" / "run.log"
        n_primary, sipm_abs = parse_log(log_path)
        values.append(sipm_abs / n_primary)
    return values


def main() -> None:
    bare = compute_series("bare")
    refla = compute_series("reflA")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["energy_keV", "bare_sipm_abs_per_gamma", "reflectorA_sipm_abs_per_gamma"])
        for e, b, r in zip(ENERGIES_KEV, bare, refla):
            w.writerow([e, f"{b:.6f}", f"{r:.6f}"])

    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)
    ax.plot(ENERGIES_KEV, bare, marker="o", lw=2, label="51 x 51 x 10, without reflector")
    ax.plot(ENERGIES_KEV, refla, marker="s", lw=2, label="51 x 51 x 10, reflector A")
    ax.set_xscale("log")
    ax.set_xticks(ENERGIES_KEV, labels=[str(e) for e in ENERGIES_KEV])
    ax.set_xlabel("energy, keV")
    ax.set_ylabel("SiPM absorptions per gamma")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_PNG)
    plt.close(fig)

    print(f"Wrote plot: {OUT_PNG}")
    print(f"Wrote summary: {OUT_CSV}")


if __name__ == "__main__":
    main()

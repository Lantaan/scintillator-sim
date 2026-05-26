#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = REPO_ROOT / "data" / "fig36_runs"
OUT_PNG = REPO_ROOT / "data" / "fig36_absorption_efficiency.png"
OUT_CSV = REPO_ROOT / "data" / "fig36_absorption_efficiency_summary.csv"

ENERGIES_KEV = [20, 50, 100, 200, 500, 1000, 4000]
N_SIM = 10000


def count_rows(csv_path: Path) -> int:
    with csv_path.open("r", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            return 0
        return sum(1 for _ in reader)


def compute_series(cfg: str) -> list[float]:
    values: list[float] = []
    for e in ENERGIES_KEV:
        src = RUN_ROOT / cfg / f"{e}keV" / "results_nt_phot_count.csv"
        if not src.exists():
            raise FileNotFoundError(f"Missing run output: {src}")
        n_counted = count_rows(src)
        values.append(100.0 * n_counted / N_SIM)
    return values


def write_summary_csv(bare: list[float], refla: list[float]) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["energy_keV", "bare_eff_percent", "reflectorA_eff_percent"])
        for e, b, r in zip(ENERGIES_KEV, bare, refla):
            writer.writerow([e, f"{b:.6f}", f"{r:.6f}"])


def make_plot(bare: list[float], refla: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=150)
    ax.plot(ENERGIES_KEV, bare, marker="o", lw=2, label="51 x 51 x 10, without reflector")
    ax.plot(ENERGIES_KEV, refla, marker="s", lw=2, label="51 x 51 x 10, reflector A")

    ax.set_xscale("log")
    ax.set_xticks(ENERGIES_KEV, labels=[str(e) for e in ENERGIES_KEV])
    ax.set_xlabel("energy, keV")
    ax.set_ylabel("Absorption efficiency, %")
    ax.set_ylim(20, 100)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG)
    plt.close(fig)


def main() -> None:
    bare = compute_series("bare")
    refla = compute_series("reflA")
    write_summary_csv(bare, refla)
    make_plot(bare, refla)
    print(f"Wrote plot: {OUT_PNG}")
    print(f"Wrote summary: {OUT_CSV}")


if __name__ == "__main__":
    main()

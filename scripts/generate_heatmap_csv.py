#!/usr/bin/env python3
"""Generate heatmap CSVs from Geant4 absorption ntuples without third-party packages."""

from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_PATTERN = re.compile(
    r"(?P<beam>[0-9]+(?:[p.][0-9]+)?)mm_"
    r"(?P<angle>[0-9]+(?:[p.][0-9]+)?)_deg_nt_absorption\.csv$"
)


def slug(value: float) -> str:
    return f"{value:g}".replace(".", "p").replace("-", "m")


def output_stem(path: Path) -> str:
    match = CASE_PATTERN.match(path.name)
    if match:
        beam_width = float(match.group("beam").replace("p", "."))
        angle = float(match.group("angle").replace("p", "."))
        return f"beam_{slug(beam_width)}mm_angle_{slug(angle)}deg"
    return path.stem.removesuffix("_nt_absorption")


def selected_inputs(input_groups: list[list[Path]] | None, glob_pattern: str) -> list[Path]:
    if input_groups:
        paths: list[Path] = []
        seen: set[Path] = set()
        for group in input_groups:
            for path in group:
                resolved = path.expanduser().resolve()
                if not resolved.is_file():
                    raise FileNotFoundError(f"Input file does not exist: {resolved}")
                if resolved not in seen:
                    paths.append(resolved)
                    seen.add(resolved)
        return paths

    glob_path = Path(glob_pattern)
    return sorted(glob_path.parent.glob(glob_path.name) if glob_path.is_absolute() else Path().glob(glob_pattern))


def bin_index(value: float, half_width: float, bin_width: float, bins: int) -> int | None:
    if not math.isfinite(value) or value < -half_width or value > half_width:
        return None
    index = int((value + half_width) / bin_width)
    return min(index, bins - 1)


def generate_heatmap(path: Path, out_dir: Path, detector_mm: float, bins: int, progress_every: int) -> None:
    half_width = detector_mm / 2.0
    bin_width = detector_mm / bins
    counts = [[0] * bins for _ in range(bins)]
    rows = 0
    finite_in_detector = 0

    with path.open("r", newline="", encoding="utf-8") as source:
        reader = csv.reader(source)
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            rows += 1
            if len(row) < 3:
                continue
            try:
                x = float(row[1])
                y = float(row[2])
            except ValueError:
                continue
            x_index = bin_index(x, half_width, bin_width, bins)
            y_index = bin_index(y, half_width, bin_width, bins)
            if x_index is None or y_index is None:
                continue
            counts[x_index][y_index] += 1
            finite_in_detector += 1
            if progress_every and rows % progress_every == 0:
                print(f"{path.name}: processed {rows:,} rows", flush=True)

    output_path = out_dir / f"{output_stem(path)}_heatmap_{bins}x{bins}.csv"
    with output_path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.writer(target)
        writer.writerow(["x_mm", "y_mm", "count"])
        for x_index in range(bins):
            x_center = -half_width + (x_index + 0.5) * bin_width
            for y_index in range(bins):
                y_center = -half_width + (y_index + 0.5) * bin_width
                writer.writerow((f"{x_center:.12g}", f"{y_center:.12g}", counts[x_index][y_index]))

    print(
        f"{path.name}: wrote {output_path} "
        f"({finite_in_detector:,} in-detector rows from {rows:,} data rows)",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        dest="input_groups",
        type=Path,
        nargs="+",
        action="append",
        help="One or more explicit absorption CSV paths. May be repeated; overrides --glob.",
    )
    parser.add_argument("--glob", default=str(REPO_ROOT / "data" / "actual" / "*_nt_absorption.csv"))
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "data" / "actual" / "heatmaps")
    parser.add_argument("--detector-mm", type=float, default=51.0)
    parser.add_argument("--bins", type=int, default=480)
    parser.add_argument("--progress-every", type=int, default=1_000_000)
    args = parser.parse_args()

    if args.detector_mm <= 0:
        raise ValueError("--detector-mm must be positive")
    if args.bins <= 0:
        raise ValueError("--bins must be positive")
    if args.progress_every < 0:
        raise ValueError("--progress-every must be zero or positive")

    paths = selected_inputs(args.input_groups, args.glob)
    if not paths:
        raise FileNotFoundError("No input absorption CSV files were selected")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        generate_heatmap(path, args.out_dir, args.detector_mm, args.bins, args.progress_every)


if __name__ == "__main__":
    main()

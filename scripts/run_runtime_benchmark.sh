#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
MACRO_DIR="${REPO_ROOT}/scripts/macros/benchmark"
OUT_DIR="${REPO_ROOT}/data/runtime_benchmark"
CASE_DIR="${OUT_DIR}/cases"
CSV="${OUT_DIR}/runtime_results.csv"

mkdir -p "${OUT_DIR}" "${CASE_DIR}"

cat > "${CSV}" <<'CSVHDR'
case_group,case_name,macro,beam_on,energy_keV,size_mm,output_mode,wall_seconds,output_files,output_total_bytes
CSVHDR

run_case() {
  local group="$1"
  local name="$2"
  local macro="$3"
  local beam="$4"
  local energy="$5"
  local size="$6"
  local outmode="$7"

  echo "[bench] Running ${group}/${name} (${macro})"

  rm -f "${REPO_ROOT}/data"/results_*.csv

  local start end elapsed
  start=$(date +%s)
  "${REPO_ROOT}/scripts/run_batch.sh" "${macro}" >/tmp/runtime_bench_${name}.log 2>&1
  end=$(date +%s)
  elapsed=$((end - start))

  local out_case_dir="${CASE_DIR}/${group}_${name}"
  mkdir -p "${out_case_dir}"
  cp "${REPO_ROOT}/data"/results_*.csv "${out_case_dir}/" 2>/dev/null || true

  local files bytes
  files=$(find "${REPO_ROOT}/data" -maxdepth 1 -type f -name 'results_*.csv' | wc -l)
  bytes=$(find "${REPO_ROOT}/data" -maxdepth 1 -type f -name 'results_*.csv' -printf '%s\n' | awk '{s+=$1} END {print s+0}')

  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "${group}" "${name}" "${macro}" "${beam}" "${energy}" "${size}" "${outmode}" "${elapsed}" "${files}" "${bytes}" >> "${CSV}"
}

run_case outputs minimal "scripts/macros/benchmark/outputs_minimal.mac" 100 662 51 minimal
run_case outputs all "scripts/macros/benchmark/outputs_all.mac" 100 662 51 all

run_case size small "scripts/macros/benchmark/size_small.mac" 100 662 20 minimal
run_case size medium "scripts/macros/benchmark/size_medium.mac" 100 662 51 minimal
run_case size large "scripts/macros/benchmark/size_large.mac" 100 662 80 minimal

run_case particles p50 "scripts/macros/benchmark/particles_50.mac" 50 662 51 minimal
run_case particles p100 "scripts/macros/benchmark/particles_100.mac" 100 662 51 minimal
run_case particles p200 "scripts/macros/benchmark/particles_200.mac" 200 662 51 minimal
run_case particles p500 "scripts/macros/benchmark/particles_500.mac" 500 662 51 minimal

run_case energy e20 "scripts/macros/benchmark/energy_20keV.mac" 100 20 51 minimal
run_case energy e100 "scripts/macros/benchmark/energy_100keV.mac" 100 100 51 minimal
run_case energy e500 "scripts/macros/benchmark/energy_500keV.mac" 100 500 51 minimal
run_case energy e1000 "scripts/macros/benchmark/energy_1000keV.mac" 100 1000 51 minimal

echo "[bench] Complete. Results: ${CSV}"

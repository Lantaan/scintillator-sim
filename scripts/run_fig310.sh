#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BASE_MAC="${REPO_ROOT}/scripts/macros/fig310/fig310_base.mac"
TMP_MAC_DIR="${REPO_ROOT}/scripts/macros/fig310/generated"
OUT_ROOT="${REPO_ROOT}/data/fig310_runs"
ENERGIES=(20 50 100 200 500 1000 2000 4000)
BEAM_ON="${BEAM_ON:-300}"

log() { printf '[fig310] %s\n' "$*"; }

build_macro() {
  local energy="$1"
  local out_mac="$2"
  sed \
    -e "s|__ENERGY_KEV__|/gun/energy ${energy} keV|g" \
    -e "s|__BEAM_ON__|${BEAM_ON}|g" \
    "${BASE_MAC}" > "${out_mac}"
}

run_case() {
  local energy="$1"
  local case_dir="${OUT_ROOT}/${energy}keV"
  local case_mac="${TMP_MAC_DIR}/${energy}keV.mac"
  mkdir -p "${case_dir}"
  if [[ -f "${case_dir}/results_nt_absorption.csv" ]]; then
    log "Skipping existing E=${energy} keV"
    return
  fi
  build_macro "${energy}" "${case_mac}"
  find "${REPO_ROOT}/data" -maxdepth 1 -type f -name 'results_*.csv' -delete || true
  log "Running E=${energy} keV"
  "${REPO_ROOT}/scripts/run_batch.sh" "${case_mac}" | tee "${case_dir}/run.log"
  local src="${REPO_ROOT}/data/results_nt_absorption.csv"
  [[ -f "${src}" ]] || { printf '[fig310] ERROR: missing %s\n' "${src}" >&2; exit 1; }
  cp "${src}" "${case_dir}/results_nt_absorption.csv"
  cp "${case_mac}" "${case_dir}/run.mac"
}

main() {
  mkdir -p "${TMP_MAC_DIR}" "${OUT_ROOT}"
  log "Using beamOn=${BEAM_ON}"
  for e in "${ENERGIES[@]}"; do
    run_case "${e}"
  done
  log "All runs complete. Outputs in ${OUT_ROOT}"
}

main "$@"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BASE_MAC="${REPO_ROOT}/scripts/macros/fig36/fig36_common_base.mac"
TMP_MAC_DIR="${REPO_ROOT}/scripts/macros/fig36/generated"
OUT_ROOT="${REPO_ROOT}/data/fig36_runs"
ENERGIES=(20 50 100 200 500 1000 4000)
BEAM_ON="${BEAM_ON:-10000}"

log() {
  printf '[fig36] %s\n' "$*"
}

build_macro() {
  local cfg="$1"
  local energy="$2"
  local out_mac="$3"

  local reflector_flag reflector_type_line
  if [[ "${cfg}" == "bare" ]]; then
    reflector_flag="/opnovice2/detector/detectorHasReflector 0"
    reflector_type_line="# no reflector type for bare"
  else
    reflector_flag="/opnovice2/detector/detectorHasReflector 1"
    reflector_type_line="/opnovice2/detector/setReflectorType 0"
  fi

  sed \
    -e "s|__REFLECTOR_FLAG__|${reflector_flag}|g" \
    -e "s|__REFLECTOR_TYPE_LINE__|${reflector_type_line}|g" \
    -e "s|__ENERGY_KEV__|/gun/energy ${energy} keV|g" \
    -e "s|__BEAM_ON__|${BEAM_ON}|g" \
    "${BASE_MAC}" > "${out_mac}"
}

run_case() {
  local cfg="$1"
  local energy="$2"
  local case_dir="${OUT_ROOT}/${cfg}/${energy}keV"
  local case_mac="${TMP_MAC_DIR}/${cfg}_${energy}keV.mac"
  local out_csv="${case_dir}/results_nt_phot_count.csv"
  local out_log="${case_dir}/run.log"

  mkdir -p "${case_dir}"
  if [[ -f "${out_csv}" ]]; then
    log "Skipping existing cfg=${cfg}, E=${energy} keV"
    return
  fi
  build_macro "${cfg}" "${energy}" "${case_mac}"
  find "${REPO_ROOT}" -maxdepth 4 -type f -name 'results_nt_phot_count.csv' -delete || true

  log "Running cfg=${cfg}, E=${energy} keV"
  "${REPO_ROOT}/scripts/run_batch.sh" "${case_mac}" | tee "${out_log}"

  local produced_csv=""
  produced_csv="$(find "${REPO_ROOT}" -maxdepth 4 -type f -name 'results_nt_phot_count.csv' -printf '%T@ %p\n' | sort -nr | head -n1 | cut -d' ' -f2- || true)"
  if [[ -n "${produced_csv}" && -f "${produced_csv}" ]]; then
    cp "${produced_csv}" "${out_csv}"
  else
    log "CSV output not found for cfg=${cfg}, E=${energy} keV (continuing with log-based metrics)"
  fi
  cp "${case_mac}" "${case_dir}/run.mac"
}

main() {
  [[ -f "${BASE_MAC}" ]] || { printf '[fig36] Missing base macro: %s\n' "${BASE_MAC}" >&2; exit 1; }
  mkdir -p "${TMP_MAC_DIR}" "${OUT_ROOT}"

  log "Using beamOn=${BEAM_ON}"
  for cfg in bare reflA; do
    for e in "${ENERGIES[@]}"; do
      run_case "${cfg}" "${e}"
    done
  done

  log "All runs complete. Archived outputs under ${OUT_ROOT}"
}

main "$@"

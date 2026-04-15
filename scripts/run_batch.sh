#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
GEANT4_SH="${HOME}/geant-install/bin/geant4.sh"
DATA_DIR="${REPO_ROOT}/data"
DEFAULT_MACRO="${REPO_ROOT}/1gamma.mac"

log() {
  printf '[batch] %s\n' "$*"
}

die() {
  printf '[batch] ERROR: %s\n' "$*" >&2
  exit 1
}

resolve_macro() {
  local input="$1"
  if [[ -z "${input}" ]]; then
    printf '%s\n' "${DEFAULT_MACRO}"
    return 0
  fi

  if [[ -f "${input}" ]]; then
    printf '%s/%s\n' "$(cd "$(dirname "${input}")" && pwd)" "$(basename "${input}")"
    return 0
  fi

  if [[ -f "${REPO_ROOT}/${input}" ]]; then
    printf '%s\n' "${REPO_ROOT}/${input}"
    return 0
  fi

  die "Macro file not found: ${input}"
}

[[ -f "${GEANT4_SH}" ]] || die "Missing Geant4 environment script: ${GEANT4_SH}"
source "${GEANT4_SH}"

APP_BIN=""
if [[ -x "${REPO_ROOT}/app-install/bin/OpNovice2" ]]; then
  APP_BIN="${REPO_ROOT}/app-install/bin/OpNovice2"
elif [[ -x "${REPO_ROOT}/app-build/OpNovice2" ]]; then
  APP_BIN="${REPO_ROOT}/app-build/OpNovice2"
else
  die "OpNovice2 binary not found. Build first (app-install/bin/OpNovice2 or app-build/OpNovice2)."
fi

MACRO_PATH="$(resolve_macro "${1:-}")"
mkdir -p "${DATA_DIR}"

log "Executable: ${APP_BIN}"
log "Macro: ${MACRO_PATH}"
log "Output directory: ${DATA_DIR}"
log "Running in batch mode..."

(
  cd "${DATA_DIR}"
  exec "${APP_BIN}" "${MACRO_PATH}"
)

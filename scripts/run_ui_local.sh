#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
GEANT4_SH="${HOME}/geant-install/bin/geant4.sh"
APP_BUILD_DIR="${REPO_ROOT}/app-build"
APP_BIN="${APP_BUILD_DIR}/OpNovice2"

log() {
  printf '[ui] %s\n' "$*"
}

die() {
  printf '[ui] ERROR: %s\n' "$*" >&2
  exit 1
}

if [[ -n "${SSH_CONNECTION:-}" || -n "${SSH_TTY:-}" ]]; then
  die "SSH session detected. This script is for local UI runs (WSLg/local Linux desktop)."
fi

[[ -f "${GEANT4_SH}" ]] || die "Missing Geant4 environment script: ${GEANT4_SH}"
source "${GEANT4_SH}"

if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
  die "No GUI display detected (DISPLAY/WAYLAND_DISPLAY unset). Start from local desktop/WSLg session."
fi

if ! geant4-config --has-feature qt >/dev/null 2>&1 || [[ "$(geant4-config --has-feature qt)" != "yes" ]]; then
  die "Current Geant4 install has Qt UI disabled. Rebuild Geant4 with Qt enabled for full Geant4 UI."
fi

mkdir -p "${APP_BUILD_DIR}"

if [[ ! -x "${APP_BIN}" ]]; then
  log "App binary not found, configuring/building app first"
  (
    cd "${APP_BUILD_DIR}"
    cmake -DCMAKE_INSTALL_PREFIX="${REPO_ROOT}/app-install" \
      -DGeant4_DIR="${HOME}/geant-install/lib/Geant4-10.7.2" \
      ..
    cmake --build . -j"$(nproc 2>/dev/null || echo 4)"
  )
fi

log "Launching OpNovice2 interactive UI from ${APP_BUILD_DIR}"
(
  cd "${APP_BUILD_DIR}"
  exec ./OpNovice2
)

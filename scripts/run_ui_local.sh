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

find_geant4_cmake_dir() {
  local config_file
  config_file="$(find "${HOME}/geant-install" -type f -name Geant4Config.cmake | head -n1 || true)"
  [[ -n "${config_file}" ]] || die "Could not locate Geant4Config.cmake under ${HOME}/geant-install"
  dirname "${config_file}"
}

if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
  die "No GUI display detected (DISPLAY/WAYLAND_DISPLAY unset). Start from local desktop/WSLg session."
fi

if ! geant4-config --has-feature qt >/dev/null 2>&1 || [[ "$(geant4-config --has-feature qt)" != "yes" ]]; then
  die "Current Geant4 install has Qt UI disabled. Run: ./scripts/setup_wsl_geant4.sh --with-qt --rebuild-geant --install-deps"
fi

mkdir -p "${APP_BUILD_DIR}"

if [[ ! -x "${APP_BIN}" ]]; then
  log "App binary not found, configuring/building app first"
  GEANT4_CMAKE_DIR="$(find_geant4_cmake_dir)"
  (
    cd "${APP_BUILD_DIR}"
    cmake -DCMAKE_INSTALL_PREFIX="${REPO_ROOT}/app-install" \
      -DGeant4_DIR="${GEANT4_CMAKE_DIR}" \
      ..
    cmake --build . -j"$(nproc 2>/dev/null || echo 4)"
  )
fi

log "Launching OpNovice2 interactive UI from ${APP_BUILD_DIR}"
(
  cd "${APP_BUILD_DIR}"
  exec ./OpNovice2
)

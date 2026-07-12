#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${REPO_ROOT}/app-build"
INSTALL_DIR="${REPO_ROOT}/app-install"
GEANT4_SH="${HOME}/geant-install/bin/geant4.sh"
JOBS="${JOBS:-$(nproc)}"

die() {
  printf '[build-app] ERROR: %s\n' "$*" >&2
  exit 1
}

[[ -f "${GEANT4_SH}" ]] || die "Missing Geant4 environment script: ${GEANT4_SH}"
source "${GEANT4_SH}"

GEANT4_CONFIG="$(find "${HOME}/geant-install" -name Geant4Config.cmake -print -quit)"
[[ -n "${GEANT4_CONFIG}" ]] || die "Could not find Geant4Config.cmake under ${HOME}/geant-install"
GEANT4_DIR="$(dirname "${GEANT4_CONFIG}")"

cmake -S "${REPO_ROOT}" -B "${BUILD_DIR}" \
  -DCMAKE_INSTALL_PREFIX="${INSTALL_DIR}" \
  -DGeant4_DIR="${GEANT4_DIR}"

cmake --build "${BUILD_DIR}" -j "${JOBS}"
cmake --install "${BUILD_DIR}"

printf '[build-app] Installed OpNovice2 to %s/bin/OpNovice2\n' "${INSTALL_DIR}"

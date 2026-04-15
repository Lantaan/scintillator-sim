#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[setup] %s\n' "$*"
}

die() {
  printf '[setup] ERROR: %s\n' "$*" >&2
  exit 1
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

GEANT_TARBALL_URL="https://geant4-data.web.cern.ch/releases/geant4.10.07.p02.tar.gz"
GEANT_TARBALL="${HOME}/geant4.10.07.p02.tar.gz"
GEANT_SRC_DIR="${HOME}/geant4.10.07.p02"
GEANT_BUILD_DIR="${HOME}/geant-build"
GEANT_INSTALL_DIR="${HOME}/geant-install"
GEANT_PKG_CACHE="${GEANT_INSTALL_DIR}/lib/Geant4-10.7.2/Geant4PackageCache.cmake"
APP_BUILD_DIR="${REPO_ROOT}/app-build"
APP_INSTALL_DIR="${REPO_ROOT}/app-install"
PATCH_FILE="${REPO_ROOT}/geant_10.7.2.patch"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 4)}"

INSTALL_DEPS=0
FORCE_CLEAN=0
WITH_QT=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --install-deps   Install required apt dependencies
  --force-clean    Remove existing Geant4 source/build/install and app build/install
  --with-qt        Try Geant4 build with Qt enabled (default: off for resilience)
  -j, --jobs N     Parallel build jobs (default: ${JOBS})
  -h, --help       Show this help

Examples:
  $(basename "$0") --install-deps --force-clean
  $(basename "$0") --jobs 8
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-deps)
      INSTALL_DEPS=1
      shift
      ;;
    --force-clean)
      FORCE_CLEAN=1
      shift
      ;;
    --with-qt)
      WITH_QT=1
      shift
      ;;
    -j|--jobs)
      [[ $# -ge 2 ]] || die "Missing value for $1"
      JOBS="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown argument: $1"
      ;;
  esac
done

[[ -f "${PATCH_FILE}" ]] || die "Patch file not found: ${PATCH_FILE}"
[[ -f "${REPO_ROOT}/CMakeLists.txt" ]] || die "Run this from within the project repository."

if [[ "${INSTALL_DEPS}" -eq 1 ]]; then
  log "Installing Ubuntu dependencies"
  sudo apt-get update
  sudo apt-get install -y \
    dpkg-dev cmake g++ gcc binutils make \
    libx11-dev libxpm-dev libxft-dev libxext-dev libxmu-dev \
    python3 libxerces-c-dev qtbase5-dev \
    expat libexpat1-dev
fi

if [[ "${FORCE_CLEAN}" -eq 1 ]]; then
  log "Cleaning previous source/build/install outputs"
  rm -rf "${GEANT_SRC_DIR}" "${GEANT_BUILD_DIR}" "${GEANT_INSTALL_DIR}" "${APP_BUILD_DIR}" "${APP_INSTALL_DIR}"
fi

if [[ ! -f "${GEANT_TARBALL}" ]]; then
  log "Downloading Geant4 source tarball"
  wget -O "${GEANT_TARBALL}" "${GEANT_TARBALL_URL}"
else
  log "Using existing tarball: ${GEANT_TARBALL}"
fi

if [[ ! -d "${GEANT_SRC_DIR}" ]]; then
  log "Extracting Geant4 source"
  tar zxf "${GEANT_TARBALL}" -C "${HOME}"
fi

apply_patch_with_fallback() {
  log "Applying project patch"
  (
    cd "${GEANT_SRC_DIR}"
    patch -p1 < "${PATCH_FILE}" || true

    local mixmax="source/externals/clhep/include/CLHEP/Random/MixMaxRng.h"
    local rej="${mixmax}.rej"
    if [[ -f "${rej}" ]]; then
      log "Patch reject detected in MixMaxRng.h; applying fallback include fix"
      grep -q 'cstdint' "${mixmax}" || sed -i '/#include <array>/a #include <cstdint>' "${mixmax}"
    fi

    grep -q 'cstdint' "${mixmax}" || die "MixMaxRng.h is missing cstdint include after patch/fallback"
    grep -q 'fltsqrt' "source/persistency/ascii/src/G4tgrEvaluator.cc" || die "G4tgrEvaluator patch was not applied"
  )
}

fix_expat_cache() {
  [[ -f "${GEANT_PKG_CACHE}" ]] || die "Geant4PackageCache.cmake not found: ${GEANT_PKG_CACHE}"
  log "Fixing EXPAT_LIBRARY entry in Geant4PackageCache.cmake"
  sed -i \
    's|geant4_set_and_check_package_variable(EXPAT_LIBRARY ""  "")|geant4_set_and_check_package_variable(EXPAT_LIBRARY "/usr/lib/x86_64-linux-gnu/libexpat.so.1" FILEPATH "Path to a library.")|' \
    "${GEANT_PKG_CACHE}"
  grep -q 'EXPAT_LIBRARY "/usr/lib/x86_64-linux-gnu/libexpat.so.1" FILEPATH' "${GEANT_PKG_CACHE}" \
    || die "Failed to patch EXPAT_LIBRARY entry in ${GEANT_PKG_CACHE}"
}

configure_build_install_geant() {
  local with_qt="$1"
  log "Configuring Geant4 (GEANT4_USE_QT=${with_qt})"
  cmake -S "${GEANT_SRC_DIR}" -B "${GEANT_BUILD_DIR}" \
    -DCMAKE_INSTALL_PREFIX="${GEANT_INSTALL_DIR}" \
    -DGEANT4_INSTALL_DATA=ON \
    -DGEANT4_USE_OPENGL_X11=ON \
    -DGEANT4_BUILD_MULTITHREADED=ON \
    -DGEANT4_USE_QT="${with_qt}"

  log "Building Geant4"
  cmake --build "${GEANT_BUILD_DIR}" -j"${JOBS}"

  log "Installing Geant4"
  cmake --install "${GEANT_BUILD_DIR}"

  [[ -f "${GEANT_INSTALL_DIR}/bin/geant4.sh" ]] || die "Missing geant4.sh after install"
  [[ -f "${GEANT_INSTALL_DIR}/lib/Geant4-10.7.2/Geant4Config.cmake" ]] || die "Missing Geant4Config.cmake after install"
}

build_app() {
  log "Configuring app against Geant4"
  rm -rf "${APP_BUILD_DIR}" "${APP_INSTALL_DIR}"
  mkdir -p "${APP_BUILD_DIR}" "${APP_INSTALL_DIR}"

  (
    cd "${APP_BUILD_DIR}"
    cmake -DCMAKE_INSTALL_PREFIX="${APP_INSTALL_DIR}" \
      -DGeant4_DIR="${GEANT_INSTALL_DIR}/lib/Geant4-10.7.2" \
      ..
  )

  log "Building app"
  local build_log
  build_log="$(mktemp)"
  if ! cmake --build "${APP_BUILD_DIR}" -j"${JOBS}" >"${build_log}" 2>&1; then
    if grep -q 'libG4visQt3D\.so: file not recognized: file format not recognized' "${build_log}"; then
      rm -f "${build_log}"
      return 99
    fi
    cat "${build_log}" >&2
    rm -f "${build_log}"
    die "App build failed"
  fi
  rm -f "${build_log}"

  log "Installing app"
  cmake --install "${APP_BUILD_DIR}"
  [[ -x "${APP_INSTALL_DIR}/bin/OpNovice2" ]] || die "Missing OpNovice2 after app install"
}

apply_patch_with_fallback

if [[ "${WITH_QT}" -eq 1 ]]; then
  configure_build_install_geant ON
else
  configure_build_install_geant OFF
fi

fix_expat_cache

set +e
build_app
build_status=$?
set -e

if [[ "${build_status}" -eq 99 ]]; then
  log "Detected broken libG4visQt3D.so; rebuilding Geant4 with Qt disabled"
  configure_build_install_geant OFF
  fix_expat_cache
  build_app
fi

log "Success"
log "Run:"
log "  source ${GEANT_INSTALL_DIR}/bin/geant4.sh"
log "  cd ${REPO_ROOT}"
log "  ./app-install/bin/OpNovice2 1gamma.mac"

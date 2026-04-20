#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[setup] %s\n' "$*"
}

die() {
  printf '[setup] ERROR: %s\n' "$*" >&2
  exit 1
}

warn() {
  printf '[setup] WARNING: %s\n' "$*" >&2
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

APP_BUILD_DIR="${REPO_ROOT}/app-build"
APP_INSTALL_DIR="${REPO_ROOT}/app-install"
PATCH_FILE="${REPO_ROOT}/geant_10.7.2.patch"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 4)}"

INSTALL_DEPS=0
FORCE_CLEAN=0
WITH_QT=1
DRY_RUN=0
GEANT_VERSION="${GEANT4_VERSION:-latest}"
APPLY_LEGACY_PATCH="auto"
REBUILD_GEANT=0

GEANT_TAG=""
GEANT_TARBALL_URL=""
GEANT_TARBALL=""
GEANT_SRC_DIR=""
GEANT_BUILD_DIR=""
GEANT_INSTALL_DIR=""
GEANT_DEFAULT_LINK="${HOME}/geant-install"

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Options:
  --geant-version V Install a specific Geant4 version (for example: 11.4.0). Default: latest stable
  --install-deps   Install required apt dependencies
  --force-clean    Remove existing Geant4 source/build/install and app build/install
  --with-qt        Build Geant4 with Qt enabled (default)
  --without-qt     Build Geant4 without Qt UI support
  --apply-legacy-patch
                   Apply geant_10.7.2.patch even when version is not 10.7.x
  --skip-legacy-patch
                   Do not apply geant_10.7.2.patch
  --dry-run        Print actions without downloading/building/installing
  --rebuild-geant  Force rebuild/reinstall Geant4 even if target install exists
  -j, --jobs N     Parallel build jobs (default: ${JOBS})
  -h, --help       Show this help

Compatibility:
  - Works on WSL and native Linux.
  - --install-deps supports apt, dnf, pacman, and zypper.

Examples:
  $(basename "$0") --install-deps --force-clean
  $(basename "$0") --geant-version 11.4.0 --install-deps
  $(basename "$0") --jobs 8
  $(basename "$0") --without-qt
  $(basename "$0") --dry-run
  $(basename "$0") --rebuild-geant
EOF
}

run_cmd() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] $*"
    return 0
  fi
  "$@"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

run_as_root() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] $* (root)"
    return 0
  fi

  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
    return 0
  fi

  if command -v sudo >/dev/null 2>&1; then
    sudo "$@"
    return 0
  fi

  die "Root privileges required for dependency installation (install sudo or run as root)."
}

download_to_stdout() {
  local url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${url}"
    return 0
  fi
  if command -v wget >/dev/null 2>&1; then
    wget -qO- "${url}"
    return 0
  fi
  return 1
}

download_file() {
  local url="$1"
  local out="$2"
  if command -v curl >/dev/null 2>&1; then
    run_cmd curl -fL -o "${out}" "${url}"
    return 0
  fi
  if command -v wget >/dev/null 2>&1; then
    run_cmd wget -O "${out}" "${url}"
    return 0
  fi
  die "Neither curl nor wget is available for downloads."
}

fetch_latest_stable_geant_version() {
  local api_url="https://api.github.com/repos/Geant4/geant4/releases/latest"
  local releases_page="https://geant4.web.cern.ch/download/all.html"
  local payload
  local tag

  if payload="$(download_to_stdout "${api_url}" 2>/dev/null)"; then
    tag="$(
      printf '%s' "${payload}" |
      tr '\n' ' ' |
      sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p'
    )"
    if [[ "${tag}" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      printf '%s\n' "${tag#v}"
      return 0
    fi
  fi

  if payload="$(download_to_stdout "${releases_page}" 2>/dev/null)"; then
    tag="$(
      printf '%s' "${payload}" |
      grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' |
      sort -Vu |
      tail -n1
    )"
    if [[ -n "${tag}" ]]; then
      printf '%s\n' "${tag}"
      return 0
    fi
  fi

  return 1
}

resolve_geant_version() {
  if [[ "${GEANT_VERSION}" == "latest" ]]; then
    log "Resolving latest stable Geant4 release"
    GEANT_VERSION="$(fetch_latest_stable_geant_version)" || die "Could not resolve latest Geant4 release."
  fi

  [[ "${GEANT_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
    || die "Invalid Geant4 version '${GEANT_VERSION}'. Expected format: MAJOR.MINOR.PATCH"

  GEANT_TAG="v${GEANT_VERSION}"
  GEANT_TARBALL_URL="https://github.com/Geant4/geant4/archive/refs/tags/${GEANT_TAG}.tar.gz"
  GEANT_TARBALL="${HOME}/geant4-${GEANT_TAG}.tar.gz"
  GEANT_SRC_DIR="${HOME}/geant4-src-${GEANT_VERSION}"
  GEANT_BUILD_DIR="${HOME}/geant-build-${GEANT_VERSION}"
  GEANT_INSTALL_DIR="${HOME}/geant-install-${GEANT_VERSION}"
}

install_dependencies() {
  local install_qt="$1"

  if command -v apt-get >/dev/null 2>&1; then
    log "Installing dependencies with apt-get"
    run_as_root apt-get update
    local packages=(
      dpkg-dev cmake g++ gcc binutils make
      libx11-dev libxpm-dev libxft-dev libxext-dev libxmu-dev
      python3 libxerces-c-dev expat libexpat1-dev
      xfonts-base xfonts-75dpi xfonts-100dpi
      ca-certificates curl tar patch
    )
    if [[ "${install_qt}" == "ON" ]]; then
      packages+=(qt6-base-dev)
    fi
    run_as_root apt-get install -y "${packages[@]}"
    return 0
  fi

  if command -v dnf >/dev/null 2>&1; then
    log "Installing dependencies with dnf"
    local packages=(
      cmake gcc-c++ gcc make binutils
      libX11-devel libXpm-devel libXft-devel libXext-devel libXmu-devel
      python3 xerces-c-devel expat expat-devel
      ca-certificates curl tar patch findutils
    )
    if [[ "${install_qt}" == "ON" ]]; then
      packages+=(qt6-qtbase-devel)
    fi
    run_as_root dnf install -y "${packages[@]}"
    return 0
  fi

  if command -v pacman >/dev/null 2>&1; then
    log "Installing dependencies with pacman"
    local packages=(
      base-devel cmake libx11 libxpm libxft libxext libxmu
      python xerces-c expat
      ca-certificates curl tar patch
    )
    if [[ "${install_qt}" == "ON" ]]; then
      packages+=(qt6-base)
    fi
    run_as_root pacman -Sy --noconfirm "${packages[@]}"
    return 0
  fi

  if command -v zypper >/dev/null 2>&1; then
    log "Installing dependencies with zypper"
    local packages=(
      cmake gcc-c++ gcc make binutils
      libX11-devel libXpm-devel libXft-devel libXext-devel libXmu-devel
      python3 xerces-c-devel libexpat-devel
      ca-certificates curl tar patch
    )
    if [[ "${install_qt}" == "ON" ]]; then
      packages+=(qt6-base-devel)
    fi
    run_as_root zypper --non-interactive install "${packages[@]}"
    return 0
  fi

  die "--install-deps is unsupported on this distro (no apt-get/dnf/pacman/zypper found)."
}

is_legacy_patch_target() {
  [[ "${GEANT_VERSION}" =~ ^10\.7\.[0-9]+$ ]]
}

apply_patch_with_fallback() {
  if [[ "${APPLY_LEGACY_PATCH}" == "never" ]]; then
    log "Skipping legacy patch by user request"
    return 0
  fi

  if [[ "${APPLY_LEGACY_PATCH}" == "auto" ]] && ! is_legacy_patch_target; then
    log "Skipping legacy patch (only needed for Geant4 10.7.x)"
    return 0
  fi

  [[ -f "${PATCH_FILE}" ]] || {
    warn "Legacy patch file not found: ${PATCH_FILE}; continuing without patch."
    return 0
  }

  log "Applying legacy project patch"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] patch -p1 < ${PATCH_FILE}"
    return 0
  fi

  (
    cd "${GEANT_SRC_DIR}"
    patch -p1 < "${PATCH_FILE}" || true

    local mixmax="source/externals/clhep/include/CLHEP/Random/MixMaxRng.h"
    local rej="${mixmax}.rej"
    if [[ -f "${rej}" && -f "${mixmax}" ]]; then
      log "Patch reject detected in MixMaxRng.h; applying fallback include fix"
      grep -q 'cstdint' "${mixmax}" || sed -i '/#include <array>/a #include <cstdint>' "${mixmax}"
    fi

    if [[ -f "${mixmax}" ]]; then
      grep -q 'cstdint' "${mixmax}" || die "MixMaxRng.h missing cstdint after legacy patch/fallback"
    fi

    local evaluator="source/persistency/ascii/src/G4tgrEvaluator.cc"
    if [[ -f "${evaluator}" ]]; then
      grep -q 'fltsqrt' "${evaluator}" || die "G4tgrEvaluator legacy patch was not applied"
    fi
  )
}

find_geant4_cmake_dir() {
  local config_file
  config_file="$(find "${GEANT_INSTALL_DIR}" -type f -name Geant4Config.cmake | head -n1 || true)"
  [[ -n "${config_file}" ]] || die "Geant4Config.cmake not found under ${GEANT_INSTALL_DIR}"
  dirname "${config_file}"
}

find_expat_library() {
  local expat_path
  if command -v ldconfig >/dev/null 2>&1; then
    expat_path="$(ldconfig -p 2>/dev/null | awk '/libexpat\.so(\.1)? / {print $NF; exit}')"
    if [[ -n "${expat_path}" && -f "${expat_path}" ]]; then
      printf '%s\n' "${expat_path}"
      return 0
    fi
  fi

  expat_path="$(find /usr/lib /usr/lib64 /lib /lib64 -type f -name 'libexpat.so*' 2>/dev/null | head -n1 || true)"
  if [[ -n "${expat_path}" ]]; then
    printf '%s\n' "${expat_path}"
    return 0
  fi

  return 1
}

fix_expat_cache_if_needed() {
  [[ -d "${GEANT_INSTALL_DIR}" ]] || return 0

  local pkg_cache
  pkg_cache="$(find "${GEANT_INSTALL_DIR}" -type f -name Geant4PackageCache.cmake 2>/dev/null | head -n1 || true)"
  [[ -n "${pkg_cache}" ]] || return 0

  if ! grep -q 'geant4_set_and_check_package_variable(EXPAT_LIBRARY ""  "")' "${pkg_cache}"; then
    return 0
  fi

  local expat_path
  expat_path="$(find_expat_library)" || {
    warn "EXPAT cache entry is empty and no libexpat path was found; leaving cache unchanged."
    return 0
  }

  log "Repairing empty EXPAT_LIBRARY entry in ${pkg_cache}"
  local escaped_expat
  escaped_expat="$(printf '%s' "${expat_path}" | sed 's/[\/&]/\\&/g')"

  run_cmd sed -i \
    "s|geant4_set_and_check_package_variable(EXPAT_LIBRARY \"\"  \"\")|geant4_set_and_check_package_variable(EXPAT_LIBRARY \"${escaped_expat}\" FILEPATH \"Path to a library.\")|" \
    "${pkg_cache}"

  if [[ "${DRY_RUN}" -eq 0 ]]; then
    grep -q "EXPAT_LIBRARY \"${expat_path}\" FILEPATH" "${pkg_cache}" \
      || die "Failed to patch EXPAT_LIBRARY entry in ${pkg_cache}"
  fi
}

configure_build_install_geant() {
  local with_qt="$1"
  log "Configuring Geant4 ${GEANT_VERSION} (GEANT4_USE_QT=${with_qt})"

  run_cmd rm -rf "${GEANT_BUILD_DIR}"
  run_cmd cmake -S "${GEANT_SRC_DIR}" -B "${GEANT_BUILD_DIR}" \
    -DCMAKE_INSTALL_PREFIX="${GEANT_INSTALL_DIR}" \
    -DGEANT4_INSTALL_DATA=ON \
    -DGEANT4_USE_OPENGL_X11=ON \
    -DGEANT4_BUILD_MULTITHREADED=ON \
    -DGEANT4_USE_QT="${with_qt}"

  log "Building Geant4"
  run_cmd cmake --build "${GEANT_BUILD_DIR}" -j"${JOBS}"

  log "Installing Geant4"
  run_cmd cmake --install "${GEANT_BUILD_DIR}"

  if [[ "${DRY_RUN}" -eq 0 ]]; then
    [[ -f "${GEANT_INSTALL_DIR}/bin/geant4.sh" ]] || die "Missing geant4.sh after install"
    find_geant4_cmake_dir >/dev/null
  fi
}

create_default_install_link() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] ln -sfn ${GEANT_INSTALL_DIR} ${GEANT_DEFAULT_LINK}"
    return 0
  fi

  if [[ -e "${GEANT_DEFAULT_LINK}" && ! -L "${GEANT_DEFAULT_LINK}" ]]; then
    local current_real
    local target_real
    current_real="$(cd "${GEANT_DEFAULT_LINK}" >/dev/null 2>&1 && pwd -P || true)"
    target_real="$(cd "${GEANT_INSTALL_DIR}" >/dev/null 2>&1 && pwd -P || true)"

    if [[ -n "${current_real}" && -n "${target_real}" && "${current_real}" == "${target_real}" ]]; then
      return 0
    fi

    local backup_path="${GEANT_DEFAULT_LINK}.backup.$(date +%Y%m%d%H%M%S)"
    log "Existing ${GEANT_DEFAULT_LINK} is a directory; moving it to ${backup_path}"
    mv "${GEANT_DEFAULT_LINK}" "${backup_path}"
  fi

  ln -sfn "${GEANT_INSTALL_DIR}" "${GEANT_DEFAULT_LINK}"
}

build_app() {
  log "Configuring app against Geant4 ${GEANT_VERSION}"
  run_cmd rm -rf "${APP_BUILD_DIR}" "${APP_INSTALL_DIR}"
  run_cmd mkdir -p "${APP_BUILD_DIR}" "${APP_INSTALL_DIR}"

  local geant4_cmake_dir
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    geant4_cmake_dir="${GEANT_INSTALL_DIR}/lib/Geant4-*"
  else
    geant4_cmake_dir="$(find_geant4_cmake_dir)"
  fi

  (
    cd "${APP_BUILD_DIR}"
    run_cmd cmake -DCMAKE_INSTALL_PREFIX="${APP_INSTALL_DIR}" \
      -DGeant4_DIR="${geant4_cmake_dir}" \
      ..
  )

  log "Building app"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    run_cmd cmake --build "${APP_BUILD_DIR}" -j"${JOBS}"
    log "Installing app"
    run_cmd cmake --install "${APP_BUILD_DIR}"
    return 0
  fi

  local build_log
  build_log="$(mktemp)"
  if ! run_cmd cmake --build "${APP_BUILD_DIR}" -j"${JOBS}" >"${build_log}" 2>&1; then
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
  run_cmd cmake --install "${APP_BUILD_DIR}"

  if [[ "${DRY_RUN}" -eq 0 ]]; then
    [[ -x "${APP_INSTALL_DIR}/bin/OpNovice2" ]] || die "Missing OpNovice2 after app install"
  fi
}

validate_environment() {
  require_cmd cmake
  require_cmd tar
  require_cmd find

  if command -v curl >/dev/null 2>&1 || command -v wget >/dev/null 2>&1; then
    :
  else
    die "curl or wget is required for Geant4 source download."
  fi
}

geant_install_ready() {
  [[ -f "${GEANT_INSTALL_DIR}/bin/geant4.sh" ]] || return 1
  find_geant4_cmake_dir >/dev/null 2>&1 || return 1

  if [[ "${WITH_QT}" -eq 1 && "${DRY_RUN}" -eq 0 ]]; then
    if ! bash -lc "source \"${GEANT_INSTALL_DIR}/bin/geant4.sh\" && geant4-config --has-feature qt 2>/dev/null | grep -qx yes"; then
      return 1
    fi
  fi

  return 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --geant-version)
      [[ $# -ge 2 ]] || die "Missing value for $1"
      GEANT_VERSION="$2"
      shift 2
      ;;
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
    --without-qt)
      WITH_QT=0
      shift
      ;;
    --apply-legacy-patch)
      APPLY_LEGACY_PATCH="always"
      shift
      ;;
    --skip-legacy-patch)
      APPLY_LEGACY_PATCH="never"
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --rebuild-geant)
      REBUILD_GEANT=1
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

[[ -f "${REPO_ROOT}/CMakeLists.txt" ]] || die "Run this from within the project repository."

validate_environment
resolve_geant_version

log "Target Geant4 version: ${GEANT_VERSION}"
log "Source URL: ${GEANT_TARBALL_URL}"

if grep -qi microsoft /proc/version 2>/dev/null; then
  log "Environment: WSL"
else
  log "Environment: native Linux"
fi

if [[ "${INSTALL_DEPS}" -eq 1 ]]; then
  configure_qt="OFF"
  if [[ "${WITH_QT}" -eq 1 ]]; then
    configure_qt="ON"
  fi
  install_dependencies "${configure_qt}"
fi

if [[ "${FORCE_CLEAN}" -eq 1 ]]; then
  log "Cleaning previous source/build/install outputs"
  run_cmd rm -rf "${GEANT_SRC_DIR}" "${GEANT_BUILD_DIR}" "${GEANT_INSTALL_DIR}" "${APP_BUILD_DIR}" "${APP_INSTALL_DIR}"
fi

if [[ "${REBUILD_GEANT}" -eq 0 ]] && geant_install_ready; then
  log "Reusing existing Geant4 install at ${GEANT_INSTALL_DIR}"
else
  if [[ ! -f "${GEANT_TARBALL}" ]]; then
    log "Downloading Geant4 source tarball"
    download_file "${GEANT_TARBALL_URL}" "${GEANT_TARBALL}"
  else
    log "Using existing tarball: ${GEANT_TARBALL}"
  fi

  if [[ ! -d "${GEANT_SRC_DIR}" ]]; then
    log "Extracting Geant4 source to ${GEANT_SRC_DIR}"
    run_cmd mkdir -p "${GEANT_SRC_DIR}"
    run_cmd tar zxf "${GEANT_TARBALL}" -C "${GEANT_SRC_DIR}" --strip-components=1
  fi

  apply_patch_with_fallback

  if [[ "${WITH_QT}" -eq 1 ]]; then
    configure_build_install_geant ON
  else
    configure_build_install_geant OFF
  fi
fi

fix_expat_cache_if_needed
create_default_install_link

set +e
build_app
build_status=$?
set -e

if [[ "${build_status}" -eq 99 ]]; then
  log "Detected broken libG4visQt3D.so; rebuilding Geant4 with Qt disabled"
  configure_build_install_geant OFF
  fix_expat_cache_if_needed
  create_default_install_link
  build_app
fi

log "Success"
log "Run:"
log "  source ${GEANT_DEFAULT_LINK}/bin/geant4.sh"
log "  cd ${REPO_ROOT}"
log "  ./app-install/bin/OpNovice2 1gamma.mac"

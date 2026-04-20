# Linux/WSL Setup Guide: Auto-Install Latest Stable Geant4

This project now uses a single setup script that can install and wire up the newest stable Geant4 release automatically.

- Script: `scripts/setup_wsl_geant4.sh`
- Supported environments: WSL (Ubuntu and similar) and native Linux
- Supported dependency managers for `--install-deps`: `apt`, `dnf`, `pacman`, `zypper`

## Quick Start

```bash
cd /mnt/d/scintillator-sim   # WSL path example
chmod +x scripts/setup_wsl_geant4.sh
./scripts/setup_wsl_geant4.sh --install-deps --force-clean
```

The script will:

1. detect the latest stable Geant4 release
2. download Geant4 source from GitHub release tag tarball
3. build and install Geant4 into a versioned directory (`~/geant-install-<version>`)
4. update `~/geant-install` symlink to the versioned install
5. configure/build/install this app against the installed Geant4

## Useful Options

```bash
# Pin a specific Geant4 release
./scripts/setup_wsl_geant4.sh --geant-version 11.4.0

# Build without Qt support
./scripts/setup_wsl_geant4.sh --without-qt

# Force legacy patch use
./scripts/setup_wsl_geant4.sh --apply-legacy-patch

# Disable legacy patch use
./scripts/setup_wsl_geant4.sh --skip-legacy-patch

# Preview commands only (no changes)
./scripts/setup_wsl_geant4.sh --dry-run

# Rebuild Geant4 even if this version is already installed
./scripts/setup_wsl_geant4.sh --rebuild-geant
```

## What Changed vs Legacy 10.7.2 Flow

1. Removed hardcoded `10.07.p02`/`Geant4-10.7.2` paths.
2. Added automatic latest stable version discovery.
3. Added explicit version override (`--geant-version`).
4. Added package-manager aware dependency installation.
5. Switched install layout to versioned directories plus stable symlink:
   - `~/geant-install-<version>`
   - `~/geant-install -> ~/geant-install-<version>`
6. Kept legacy 10.7 patch support, but made it conditional:
   - auto-applies only for `10.7.x` by default
   - controllable via flags
7. Kept Qt fallback recovery path:
   - if `libG4visQt3D.so` link issue is detected, script rebuilds with Qt disabled
8. EXPAT cache repair is now conditional and path-discovered, not hardcoded.
9. Added Geant4-install reuse mode (default) plus `--rebuild-geant` override.
10. Updated project sources for Geant4 11.x API compatibility:
   - `g4csv.hh` fallback to `G4CsvAnalysisManager.hh`
   - conditional handling for removed `SetSpline(true)` calls
   - scintillation property names switched to 11.x-compatible keys when needed
   - world absorption length now set as a vector property (11.x-safe)

## Verification Checklist

After a successful run:

```bash
test -f ~/geant-install/bin/geant4.sh && echo "geant4.sh OK"
find ~/geant-install -name Geant4Config.cmake | head -n1
test -x /mnt/d/scintillator-sim/app-install/bin/OpNovice2 && echo "OpNovice2 OK"
```

Then run:

```bash
source ~/geant-install/bin/geant4.sh
cd /mnt/d/scintillator-sim
./app-install/bin/OpNovice2 1gamma.mac
```

## Notes on Legacy Patch

The file `geant_10.7.2.patch` exists for old Geant4 versions and is not generally needed for modern Geant4 (`11.x`).

- Default behavior:
  - apply patch automatically only for `10.7.x`
  - skip patch for `11.x` and newer
- Override with:
  - `--apply-legacy-patch`
  - `--skip-legacy-patch`

## Troubleshooting

### WSL permission failure from Windows host (`E_ACCESSDENIED`)

Run WSL commands from an elevated terminal if needed, or invoke setup from inside a WSL shell directly.

### Qt3D shared library link failure

Symptom:

- `libG4visQt3D.so: file not recognized: file format not recognized`

Resolution:

- The script detects this and automatically rebuilds Geant4 with Qt disabled, then rebuilds the app.

### Existing `~/geant-install` directory blocks symlink update

Symptom:

- runtime still loads old Geant4 environment after a new install

Resolution:

- script now detects non-symlink `~/geant-install`, moves it to a timestamped backup, and creates a correct symlink to `~/geant-install-<version>`.

### No package manager match for `--install-deps`

If your distro is not `apt`/`dnf`/`pacman`/`zypper`, install equivalent packages manually and run script without `--install-deps`.

# Complete Setup Guide: Geant4 10.07.p02 on WSL Ubuntu 24.04

> Legacy guide for pinned Geant4 10.7.2 setups.
> For the current auto-latest Linux/WSL flow, use:
> `docs/SETUP_LINUX_GEANT4_LATEST.md`

# TLDR
Run `scripts/setup_wsl_geant4.sh`. Make sure you have Geant4 installed (most reliably version 10.07.p02), and the script has permission to be executed.

# Full Guide
Everything beyond this line is LLM generated, and is probably best parsed by one.

This document is a full, reproducible walkthrough for setting up this project on:

- Windows host
- WSL2 Ubuntu 24.04
- Geant4 `10.07.p02` (`Geant4-10.7.2`)

It includes exact commands, verification steps, known pitfalls, and fixes.

## 1. Goal

By the end of this guide, you will have:

1. Geant4 installed at `~/geant-install`
2. This app built and installed at `/mnt/d/scintillator-sim/app-install`
3. `OpNovice2` executable running with macro files

## 1.1 Resilient Automated Setup (Recommended)

A hardened setup script is included:

- `scripts/setup_wsl_geant4.sh`

It adds resilience for common failures:

- applies `geant_10.7.2.patch` with fallback when CRLF/LF causes a rejected hunk
- validates patch effects before continuing
- fixes `EXPAT_LIBRARY` entry in Geant4 package cache with correct macro signature
- builds the app and auto-detects the known `libG4visQt3D.so` linker pitfall
- if Qt3D linker corruption is detected, automatically rebuilds Geant4 with Qt disabled and retries app build

Run it from WSL:

```bash
cd /mnt/d/scintillator-sim
chmod +x scripts/setup_wsl_geant4.sh
./scripts/setup_wsl_geant4.sh --install-deps --force-clean
```

Useful options:

- `--jobs 8` to speed up builds
- `--with-qt` to force Qt-enabled build (default behavior)
- `--without-qt` for headless/minimal environments

Compatibility notes:

- Works as-is on WSL Ubuntu and native Ubuntu/Debian Linux.
- On non-Debian distributions (Fedora/Arch/etc.), use the script without `--install-deps`, install equivalent packages manually, and then run the script.
- The EXPAT cache repair currently uses Debian/Ubuntu path:
  - `/usr/lib/x86_64-linux-gnu/libexpat.so.1`
- On other layouts/architectures, update that EXPAT path in `scripts/setup_wsl_geant4.sh`.

## 2. Known Working Layout

These paths are used throughout the guide:

- Project repo (WSL view): `/mnt/d/scintillator-sim`
- Geant4 source: `~/geant4.10.07.p02`
- Geant4 build dir: `~/geant-build`
- Geant4 install dir: `~/geant-install`
- App build dir: `/mnt/d/scintillator-sim/app-build`
- App install dir: `/mnt/d/scintillator-sim/app-install`

## 3. Prerequisites

Open Ubuntu in WSL and install dependencies:

```bash
sudo apt-get update
sudo apt-get install -y \
  dpkg-dev cmake g++ gcc binutils make \
  libx11-dev libxpm-dev libxft-dev libxext-dev libxmu-dev \
  python3 libxerces-c-dev qtbase5-dev \
  expat libexpat1-dev
```

Notes:

- `expat` and `libexpat1-dev` are required to avoid EXPAT cache issues in Geant4 package config.
- `qtbase5-dev` is installed, but this guide disables Geant4 Qt during final build because Qt3D produced a broken shared object in this environment (details in Troubleshooting).

## 4. Download and Unpack Geant4

```bash
cd ~
wget -O geant4.10.07.p02.tar.gz https://geant4-data.web.cern.ch/releases/geant4.10.07.p02.tar.gz
rm -rf geant4.10.07.p02 geant-build geant-install
tar zxf geant4.10.07.p02.tar.gz
```

## 5. Apply Project Patch

From Geant4 source root:

```bash
cd ~/geant4.10.07.p02
patch -p1 < /mnt/d/scintillator-sim/geant_10.7.2.patch || true
```

Why `|| true`:

- One hunk can fail due to line-ending differences (CRLF/LF mismatch) while the other hunk applies.
- The failed hunk is typically in `MixMaxRng.h`.

If patch creates:

- `source/externals/clhep/include/CLHEP/Random/MixMaxRng.h.rej`

then apply the missing include manually:

```bash
grep -q 'cstdint' source/externals/clhep/include/CLHEP/Random/MixMaxRng.h || \
  sed -i '/#include <array>/a #include <cstdint>' source/externals/clhep/include/CLHEP/Random/MixMaxRng.h
```

Verify both patch effects:

```bash
grep -n 'cstdint' source/externals/clhep/include/CLHEP/Random/MixMaxRng.h
grep -n 'fltsqrt\|setFunction("sqrt"' source/persistency/ascii/src/G4tgrEvaluator.cc
```

Expected:

- `#include <cstdint>` appears in `MixMaxRng.h`
- `fltsqrt` symbol and `setFunction("sqrt", (*fltsqrt));` appear in `G4tgrEvaluator.cc`

## 6. Configure, Build, and Install Geant4

Use this known-good configuration:

```bash
cmake -S ~/geant4.10.07.p02 -B ~/geant-build \
  -DCMAKE_INSTALL_PREFIX=~/geant-install \
  -DGEANT4_INSTALL_DATA=ON \
  -DGEANT4_USE_OPENGL_X11=ON \
  -DGEANT4_BUILD_MULTITHREADED=ON \
  -DGEANT4_USE_QT=OFF

cmake --build ~/geant-build -j4
cmake --install ~/geant-build
```

Important:

- `GEANT4_USE_QT=OFF` is intentional in this environment.
- With Qt enabled, `libG4visQt3D.so` was generated but malformed and caused linker failures for this project.

## 7. Fix EXPAT Entry in Geant4PackageCache.cmake

Edit:

- `~/geant-install/lib/Geant4-10.7.2/Geant4PackageCache.cmake`

Replace the EXPAT library line with:

```cmake
geant4_set_and_check_package_variable(EXPAT_LIBRARY "/usr/lib/x86_64-linux-gnu/libexpat.so.1" FILEPATH "Path to a library.")
```

You can patch it from shell:

```bash
sed -i \
  's|geant4_set_and_check_package_variable(EXPAT_LIBRARY ""  "")|geant4_set_and_check_package_variable(EXPAT_LIBRARY "/usr/lib/x86_64-linux-gnu/libexpat.so.1" FILEPATH "Path to a library.")|' \
  ~/geant-install/lib/Geant4-10.7.2/Geant4PackageCache.cmake
```

Verify:

```bash
grep -n 'EXPAT_LIBRARY' ~/geant-install/lib/Geant4-10.7.2/Geant4PackageCache.cmake
```

## 8. Verify Geant4 Installation

Run:

```bash
test -f ~/geant-install/lib/Geant4-10.7.2/Geant4Config.cmake && echo "Geant4Config OK"
test -f ~/geant-install/bin/geant4.sh && echo "geant4.sh OK"
```

Optional:

```bash
ls ~/geant-install/lib | head -n 30
```

## 9. Build and Install This Project

```bash
cd /mnt/d/scintillator-sim
rm -rf app-build app-install
mkdir -p app-build app-install
cd app-build

cmake -DCMAKE_INSTALL_PREFIX=../app-install \
  -DGeant4_DIR=$HOME/geant-install/lib/Geant4-10.7.2 \
  ..

cmake --build . -j4
cmake --install .
```

Expected output includes:

- `Built target OpNovice2`
- install to `.../app-install/bin/OpNovice2`

## 10. Run OpNovice2

From WSL:

```bash
source ~/geant-install/bin/geant4.sh
cd /mnt/d/scintillator-sim
./app-install/bin/OpNovice2 1gamma.mac
```

Alternative macros:

```bash
./app-install/bin/OpNovice2 1.mac
./app-install/bin/OpNovice2 vis.mac
```

Interactive mode:

```bash
./app-install/bin/OpNovice2
```

## 10.1 Local UI Launch (Recommended)

Use the local UI helper script (works on WSLg and native Linux desktop sessions):

```bash
cd /mnt/d/scintillator-sim
./scripts/run_ui_local.sh
```

What it does:

- sources `~/geant-install/bin/geant4.sh`
- ensures this is a local desktop session (fails fast on SSH)
- checks that GUI display variables exist
- builds app if missing
- starts interactive UI from `app-build`

Expected result:

- OpenGL window opens
- terminal reaches Geant4 prompt `Idle>`

## 11. Troubleshooting

### A. Patch hunk failure in MixMaxRng.h

Symptom:

- `Hunk #1 FAILED ... MixMaxRng.h`
- compile errors around `std::uint32_t` / `myID_t`

Fix:

1. Add `#include <cstdint>` after `#include <array>` in `MixMaxRng.h`.
2. Rebuild Geant4.

### B. Link error: libG4visQt3D.so file format not recognized

Symptom during app link:

- `/home/<user>/geant-install/lib/libG4visQt3D.so: file not recognized: file format not recognized`

Root cause in this environment:

- Qt3D shared object generated in a malformed state when Qt-enabled Geant4 build was used.

Fix:

1. Reconfigure Geant4 with `-DGEANT4_USE_QT=OFF`
2. Rebuild and reinstall Geant4
3. Rebuild the app

### C. CMake error in Geant4PackageCache.cmake EXPAT macro

Symptom:

- `geant4_set_and_check_package_variable Macro invoked with incorrect arguments`

Cause:

- EXPAT line format not matching expected macro signature.

Fix:

- Ensure line is exactly:

```cmake
geant4_set_and_check_package_variable(EXPAT_LIBRARY "/usr/lib/x86_64-linux-gnu/libexpat.so.1" FILEPATH "Path to a library.")
```

### D. WSL access denied from Windows shell

Symptom:

- `Wsl/.../E_ACCESSDENIED`

Fix:

- Run commands from an elevated terminal / ensure WSL service permissions are available.
- If using an automation/sandbox tool, execute WSL commands with elevated permissions.

### E. UI over SSH fails or no render

Symptom:

- UI starts but no image/window appears
- remote rendering errors

Fix:

- Use local WSLg/native desktop session, not SSH session.
- Run via:

```bash
./scripts/run_ui_local.sh
```

The script intentionally aborts if `SSH_CONNECTION`/`SSH_TTY` is set.

## 10.2 Batch Launch (No UI, CSVs in data/)

Use the batch helper script:

```bash
cd /mnt/d/scintillator-sim
./scripts/run_batch.sh
```

With explicit macro:

```bash
./scripts/run_batch.sh 1.mac
./scripts/run_batch.sh /absolute/path/to/your_macro.mac
```

Behavior:

- runs `OpNovice2` in batch mode by passing a macro argument
- if no macro is provided, defaults to `1gamma.mac`
- creates/uses `/mnt/d/scintillator-sim/data`
- executes from `data/`, so generated `results_*.csv` are written there

## 12. Maintenance and Rebuild Tips

### Rebuild app only

```bash
cd /mnt/d/scintillator-sim/app-build
cmake --build . -j4
```

### Clean app build

```bash
cd /mnt/d/scintillator-sim
rm -rf app-build app-install
```

### Reconfigure Geant4 from scratch

```bash
rm -rf ~/geant-build ~/geant-install
cmake -S ~/geant4.10.07.p02 -B ~/geant-build \
  -DCMAKE_INSTALL_PREFIX=~/geant-install \
  -DGEANT4_INSTALL_DATA=ON \
  -DGEANT4_USE_OPENGL_X11=ON \
  -DGEANT4_BUILD_MULTITHREADED=ON \
  -DGEANT4_USE_QT=OFF
cmake --build ~/geant-build -j4
cmake --install ~/geant-build
```

## 13. One-Shot Command Checklist

If you already have dependencies, this is the short reproducible flow:

```bash
cd ~
wget -O geant4.10.07.p02.tar.gz https://geant4-data.web.cern.ch/releases/geant4.10.07.p02.tar.gz
rm -rf geant4.10.07.p02 geant-build geant-install
tar zxf geant4.10.07.p02.tar.gz
cd geant4.10.07.p02
patch -p1 < /mnt/d/scintillator-sim/geant_10.7.2.patch || true
grep -q 'cstdint' source/externals/clhep/include/CLHEP/Random/MixMaxRng.h || sed -i '/#include <array>/a #include <cstdint>' source/externals/clhep/include/CLHEP/Random/MixMaxRng.h
cmake -S ~/geant4.10.07.p02 -B ~/geant-build -DCMAKE_INSTALL_PREFIX=~/geant-install -DGEANT4_INSTALL_DATA=ON -DGEANT4_USE_OPENGL_X11=ON -DGEANT4_BUILD_MULTITHREADED=ON -DGEANT4_USE_QT=OFF
cmake --build ~/geant-build -j4
cmake --install ~/geant-build
sed -i 's|geant4_set_and_check_package_variable(EXPAT_LIBRARY ""  "")|geant4_set_and_check_package_variable(EXPAT_LIBRARY "/usr/lib/x86_64-linux-gnu/libexpat.so.1" FILEPATH "Path to a library.")|' ~/geant-install/lib/Geant4-10.7.2/Geant4PackageCache.cmake
cd /mnt/d/scintillator-sim
rm -rf app-build app-install
mkdir -p app-build app-install
cd app-build
cmake -DCMAKE_INSTALL_PREFIX=../app-install -DGeant4_DIR=$HOME/geant-install/lib/Geant4-10.7.2 ..
cmake --build . -j4
cmake --install .
```

Then run:

```bash
source ~/geant-install/bin/geant4.sh
cd /mnt/d/scintillator-sim
./app-install/bin/OpNovice2 1gamma.mac
```

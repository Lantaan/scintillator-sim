# Scintillator Simulation Setup

This repository now targets the newest available **stable** Geant4 release automatically.

Primary setup script:

- `scripts/setup_wsl_geant4.sh`

The script works on WSL and native Linux, and can:

- auto-resolve the latest stable Geant4 version
- install dependencies on `apt`, `dnf`, `pacman`, and `zypper`
- build/install Geant4 and this project
- create/update `~/geant-install` symlink to the installed Geant4 version

For a complete guide (including troubleshooting and verification), see:

- [`docs/SETUP_LINUX_GEANT4_LATEST.md`](docs/SETUP_LINUX_GEANT4_LATEST.md)

Local UI launch (WSLg/native Linux desktop):
```bash
./scripts/run_ui_local.sh
```

Batch launch (no UI, writes CSVs to `data/`, can be used via ssh):
```bash
./scripts/run_batch.sh [optional_macro_path]
```

Note that you may have to add permissions to execute the scripts:

```bash
chmod +x ./scripts/run_ui_local.sh
chmod +x ./scripts/run_batch.sh
chmod +x ./scripts/setup_wsl_geant4.sh
```

# Scintillator Simulation Setup

This repository targets Geant4 `10.07.p02` (`Geant4-10.7.2`) on WSL Ubuntu.

For a complete, reproducible, end-to-end guide (including troubleshooting and verification), see:

- [`docs/SETUP_WSL_GEANT4_10_7_2.md`](docs/SETUP_WSL_GEANT4_10_7_2.md)

Local UI launch (WSLg/native Linux desktop):

- `./scripts/run_ui_local.sh`

Batch launch (no UI, writes CSVs to `data/`):

- `./scripts/run_batch.sh [optional_macro_path]`

Note that you may have to add permissions to execute the scripts:

```bash
chmod +x ./scripts/run_ui_local.sh
chmod +x ./scripts/run_batch.sh
chmod +x ./scripts/setup_geant4_10_7_2.sh
```
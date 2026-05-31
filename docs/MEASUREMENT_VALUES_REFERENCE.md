# Scintillator Simulation Measurement Values Reference

This document explains all data values defined in the simulation outputs, what they mean physically, whether they are configurable from `.mac`, and why they may be missing or zero.

## Quick file-to-ntuple mapping

These CSV files are written in the `data/` directory and correspond to ntuple indices in Geant4 analysis activation commands.

| Output file                      | Ntuple index | Ntuple name       | Physical meaning (short)                                                                             |
|----------------------------------|--------------|-------------------|------------------------------------------------------------------------------------------------------|
| `results_nt_phot_count.csv`      | 0            | `phot_count`      | Event-level scintillation photon yield and depth-bin counts.                                         |
| `results_nt_absorption.csv`      | 1            | `absorption`      | XY positions where optical photons are absorbed in SiPM volumes.                                     |
| `results_nt_scintillation.csv`   | 2            | `scintillation`   | Energy spectrum of emitted scintillation optical photons.                                            |
| `results_nt_scint_depth.csv`     | 3            | `scint_depth`     | Mean scintillation production depth per event (z).                                                   |
| `results_nt_abs_sp.csv`          | 4            | `abs_sp`          | Energy spectrum of optical photons absorbed in SiPM volumes.                                         |
| `results_nt_status.csv`          | 5            | `status`          | Per-event optical interaction counters (absorptions, reflections, refractions, boundary absorption). |
| `results_nt_pr_int.csv`          | 6            | `pr_int`          | Primary gamma interaction records: depth, process type, track id, energy.                            |
| `results_nt_scint_depth_std.csv` | 7            | `scint_depth_std` | Event-level spread (standard deviation) of scintillation depth.                                      |
| `results_nt_scat_angles.csv`     | 8            | `scat_angles`     | Gamma direction/energy before vs after scattering (Compton branch).                                  |

Related histogram CSVs (not ntuples):

| Output file              | Histogram name | Physical meaning (short)                      |
|--------------------------|----------------|-----------------------------------------------|
| `results_h2_absXY.csv`   | `absXY`        | 2D map of SiPM absorption positions.          |
| `results_h2_X_ev.csv`    | `X_ev`         | X-position distribution vs event axis.        |
| `results_h2_R_ev.csv`    | `R_ev`         | Radial absorption distribution vs event axis. |
| `results_h1_sc_spec.csv` | `sc_spec`      | Scintillation energy spectrum histogram.      |
| `results_h1_absR.csv`    | `absR`         | Radial distribution of absorbed photons.      |
| `results_h1_absX.csv`    | `absX`         | X distribution of absorbed photons.           |

## How output activation works

The analysis system is controlled in macro files (for example [`default.mac`](/D:/scintillator-sim/default.mac)):

- `/analysis/setActivation 1` enables analysis output globally.
- For Geant4 11.4.x, avoid `/analysis/ntuple/setActivationToAll 0`; use individual `/analysis/ntuple/setActivation <index> 0` commands instead.
- `/analysis/ntuple/setActivation <index> 1` enables one ntuple by index.

If an ntuple is not activated, it will not be written even if code fills it.

All ntuples/histograms are declared in [`src/HistoManager.cc`](/D:/scintillator-sim/src/HistoManager.cc).

## Ntuple values

### Ntuple 0: `phot_count` (number of scintillation photons per event)

Defined in [`src/HistoManager.cc:72`](/D:/scintillator-sim/src/HistoManager.cc:72), filled in [`src/EventAction.cc:70`](/D:/scintillator-sim/src/EventAction.cc:70).

| Value                     | Physical meaning                                                                             | Configurable from `.mac`?                                           | Why it may not be written                                                                                 |
|---------------------------|----------------------------------------------------------------------------------------------|---------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| `eventID`                 | Event number (one primary history).                                                          | Indirectly (`/run/beamOn` controls how many events exist).          | Ntuple 0 not activated, or event has `ScintPhotons == 0` (row is written only when scintillation exists). |
| `counts`                  | Total number of scintillation optical photons created in this event (light yield per event). | Not directly. Depends on geometry/material/source/physics settings. | Same as above.                                                                                            |
| `counts_0` ... `counts_9` | Photon counts in 10 hardcoded depth slices (z bins) where scintillation was produced.        | Not from `.mac` (bin edges are hardcoded in code).                  | Same as above. Also a bin can be zero if no scintillation happened in that depth slice.                   |

Depth-bin logic is implemented in [`include/EventAction.hh:46`](/D:/scintillator-sim/include/EventAction.hh:46).

### Ntuple 1: `absorption` (XY absorption position)

Defined in [`src/HistoManager.cc:103`](/D:/scintillator-sim/src/HistoManager.cc:103). Intended fill code exists but is commented out in [`src/SteppingAction.cc:129`](/D:/scintillator-sim/src/SteppingAction.cc:129).

| Value     | Physical meaning                                                         | Configurable from `.mac`? | Why it may not be written             |
|-----------|--------------------------------------------------------------------------|---------------------------|---------------------------------------|
| `eventID` | Event where optical photon absorption happened.                          | Indirectly.               | Fill lines are commented out in code. |
| `x`, `y`  | XY coordinate of absorbed optical photon (sensor-plane hit map concept). | Not directly.             | Fill lines are commented out in code. |

### Ntuple 2: `scintillation` (scintillation spectrum)

Defined in [`src/HistoManager.cc:110`](/D:/scintillator-sim/src/HistoManager.cc:110). Fill path in [`src/SteppingAction.cc:295`](/D:/scintillator-sim/src/SteppingAction.cc:295).

| Value    | Physical meaning                                                                          | Configurable from `.mac`?                                                                                  | Why it may not be written                                                                                                                                          |
|----------|-------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `energy` | Energy of each emitted scintillation optical photon (spectrum; wavelength/color content). | Ntuple activation is configurable. Spectrum itself depends on material properties in code/material tables. | Hardcoded switch `scint_spectrum = 0` in [`src/SteppingAction.cc:71`](/D:/scintillator-sim/src/SteppingAction.cc:71) disables writing even if ntuple is activated. |

### Ntuple 3: `scint_depth` (mean scintillation depth per event)

Defined in [`src/HistoManager.cc:115`](/D:/scintillator-sim/src/HistoManager.cc:115), row written in [`src/EventAction.cc:87`](/D:/scintillator-sim/src/EventAction.cc:87).

| Value     | Physical meaning                                            | Configurable from `.mac`? | Why it may not be written                                                                                                                                                      |
|-----------|-------------------------------------------------------------|---------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `eventID` | Event number.                                               | Indirectly.               | Ntuple not activated, or no scintillation in event (outer write condition).                                                                                                    |
| `z`       | Intended mean z-depth of scintillation production in event. | Not directly.             | Currently remains 0 because mean update call is commented out (`MeanScintDepth_ev` not used) in [`src/SteppingAction.cc:280`](/D:/scintillator-sim/src/SteppingAction.cc:280). |

### Ntuple 4: `abs_sp` (absorbed-photon spectrum)

Defined in [`src/HistoManager.cc:121`](/D:/scintillator-sim/src/HistoManager.cc:121), fill path in [`src/SteppingAction.cc:137`](/D:/scintillator-sim/src/SteppingAction.cc:137).

| Value    | Physical meaning                                              | Configurable from `.mac`?            | Why it may not be written                                                                                                            |
|----------|---------------------------------------------------------------|--------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `energy` | Energy of optical photons at absorption in SiPM-like volumes. | Ntuple activation yes; fill gate no. | Hardcoded switch `abs_spectrum = 0` in [`src/SteppingAction.cc:70`](/D:/scintillator-sim/src/SteppingAction.cc:70) disables writing. |

### Ntuple 5: `status` (optical-photon interaction counters per event)

Defined in [`src/HistoManager.cc:126`](/D:/scintillator-sim/src/HistoManager.cc:126), written in [`src/EventAction.cc:92`](/D:/scintillator-sim/src/EventAction.cc:92).

| Value             | Physical meaning                                                                   | Configurable from `.mac`?              | Why it may be zero or missing                                                                                                                                                       |
|-------------------|------------------------------------------------------------------------------------|----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `abs_SiPM`        | Number of optical photons absorbed in SiPM volumes in the event.                   | Indirectly (geometry/source/material). | Zero if no photons get absorbed in SiPM; missing if ntuple inactive or no scintillation event.                                                                                      |
| `abs_Scint`       | Number of optical photons absorbed in scintillator volume.                         | Indirectly.                            | Same reasons.                                                                                                                                                                       |
| `abs_SiPM_prior`  | Absorbed in SiPM before first significant boundary progression (track flag logic). | Not user-toggle.                       | Can be zero naturally; also depends on volume-name matching branch.                                                                                                                 |
| `abs_Scint_prior` | Same as above for scintillator.                                                    | Not user-toggle.                       | Same reasons.                                                                                                                                                                       |
| `tot_int_ref`     | Total internal reflections count in event.                                         | Not from `.mac` directly.              | Boundary-status counting block is hard-disabled by `status = 0` in [`src/SteppingAction.cc:69`](/D:/scintillator-sim/src/SteppingAction.cc:69), so this stays zero in current code. |
| `fres_refrac`     | Fresnel refraction count (interface transmission with direction change).           | Not directly.                          | Same hard-disabled boundary block.                                                                                                                                                  |
| `fres_refl`       | Fresnel reflection count (specular interface reflection).                          | Not directly.                          | Same hard-disabled boundary block.                                                                                                                                                  |
| `bound_abs`       | Boundary-surface absorption count.                                                 | Not directly.                          | Same hard-disabled boundary block.                                                                                                                                                  |
| `lamb_refl`       | Lambertian (diffuse) reflection count.                                             | Not directly.                          | Same hard-disabled boundary block.                                                                                                                                                  |
| `spike_refl`      | Specular spike reflection count.                                                   | Not directly.                          | Same hard-disabled boundary block.                                                                                                                                                  |

### Ntuple 6: `pr_int` (primary gamma interaction record)

Defined in [`src/HistoManager.cc:140`](/D:/scintillator-sim/src/HistoManager.cc:140), filled in [`src/SteppingAction.cc:309`](/D:/scintillator-sim/src/SteppingAction.cc:309).

| Value           | Physical meaning                                                    | Configurable from `.mac`? | Why it may not be written                                                                                               |
|-----------------|---------------------------------------------------------------------|---------------------------|-------------------------------------------------------------------------------------------------------------------------|
| `eventID`       | Event number.                                                       | Indirectly.               | Ntuple not activated; or no qualifying gamma interaction in tracked steps.                                              |
| `TrackID`       | Geant4 track ID of the gamma.                                       | No direct `.mac` toggle.  | Same reasons.                                                                                                           |
| `pr_int_depth`  | Z position of gamma interaction (`conv`, `compt`, `phot` branches). | No direct `.mac` toggle.  | Same reasons.                                                                                                           |
| `interactionID` | Encoded interaction type: `0=conv`, `1=compt`, `2=phot`.            | No direct `.mac` toggle.  | Same reasons.                                                                                                           |
| `energy_track`  | Gamma kinetic energy at interaction step (keV).                     | No direct `.mac` toggle.  | Potentially unreliable placement: fill line appears after `AddNtupleRow` in code, so value can be stale/mis-associated. |

### Ntuple 7: `scint_depth_std` (depth spread)

Defined in [`src/HistoManager.cc:150`](/D:/scintillator-sim/src/HistoManager.cc:150).

| Value | Physical meaning                                             | Configurable from `.mac`?   | Why it may not be written                                                                              |
|-------|--------------------------------------------------------------|-----------------------------|--------------------------------------------------------------------------------------------------------|
| `z`   | Intended standard deviation (spread) of scintillation depth. | Activation is configurable. | Fill code is commented out in [`src/EventAction.cc:105`](/D:/scintillator-sim/src/EventAction.cc:105). |

### Ntuple 8: `scat_angles` (gamma scattering angles)

Defined in [`src/HistoManager.cc:155`](/D:/scintillator-sim/src/HistoManager.cc:155), fill path in Compton branch [`src/SteppingAction.cc:348`](/D:/scintillator-sim/src/SteppingAction.cc:348).

| Value              | Physical meaning                                   | Configurable from `.mac`? | Why it may not be written                                                                                                                        |
|--------------------|----------------------------------------------------|---------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| `eventID`          | Event number.                                      | Indirectly.               | Ntuple not activated, and additional code gate disabled.                                                                                         |
| `phi_0`, `theta_0` | Initial gamma direction angles before interaction. | No direct `.mac` toggle.  | `theta` flag is hard-set `false` in [`src/SteppingAction.cc:73`](/D:/scintillator-sim/src/SteppingAction.cc:73), so write branch never executes. |
| `phi`, `theta`     | Post-interaction gamma angles.                     | Same as above.            | Same reason.                                                                                                                                     |
| `Ekin_0`, `Ekin_1` | Gamma kinetic energy before and after interaction. | Same as above.            | Same reason.                                                                                                                                     |

## Histograms (H1/H2)

Histograms are created in [`src/HistoManager.cc:90`](/D:/scintillator-sim/src/HistoManager.cc:90), but most fill calls are currently commented or behind disabled code switches.

| Histogram name | Physical meaning                            | Configurable from `.mac`?              | Why it may be empty                                                    |
|----------------|---------------------------------------------|----------------------------------------|------------------------------------------------------------------------|
| `absXY`        | XY map of absorbed optical photons in SiPM. | Not with current macros.               | Fill call commented out.                                               |
| `X_ev`         | X-position vs event distribution.           | Not with current macros.               | Fill call commented out.                                               |
| `R_ev`         | Radial position vs event distribution.      | Indirectly (source/geometry)           | This one is actively filled in current code at SiPM absorption branch. |
| `sc_spec`      | Scintillation spectrum histogram.           | No direct macro gate for local switch. | Behind `scint_spectrum = 0`.                                           |
| `absR`         | Radial absorption distribution.             | No direct macro gate for local switch. | Fill call commented out.                                               |
| `absX`         | X absorption distribution.                  | No direct macro gate for local switch. | Fill call commented out.                                               |

## Run summary values (printed to console)

Run totals are accumulated in [`src/Run.cc`](/D:/scintillator-sim/src/Run.cc) and printed in [`src/Run.cc:125`](/D:/scintillator-sim/src/Run.cc:125).

| Value                                                                  | Physical meaning                                       | Configurable from `.mac`?                      | Why it may be zero                                                                            |
|------------------------------------------------------------------------|--------------------------------------------------------|------------------------------------------------|-----------------------------------------------------------------------------------------------|
| `pair productions`, `Compton scattering`, `Photoelectric effect`       | Total primary gamma interaction-channel counts in run. | Indirectly (energy/material/physics settings). | Channel may be physically rare at current energy/material.                                    |
| `Total number of scintillation photons created`                        | Overall light yield for run.                           | Indirectly.                                    | Zero if no energy deposition yields scintillation.                                            |
| `OpAbsorption`                                                         | Total optical-photon absorptions.                      | Indirectly.                                    | Zero if no optical photons or no absorptions.                                                 |
| `OpAbsorption in SiPM`                                                 | Absorptions in SiPM volumes.                           | Indirectly (geometry + transport).             | Zero if photons do not reach/absorb there.                                                    |
| `OpAbsorption in Scintillator`                                         | Self-absorption in scintillator.                       | Indirectly (material + path lengths).          | Zero if absorption length is long vs path.                                                    |
| Surface-process counts (`Fresnel`, `TIR`, `Lambertian`, `Spike`, etc.) | Optical boundary behavior statistics.                  | Indirectly.                                    | With current code path for detailed boundary counting disabled in stepping, many remain zero. |

## What is configurable vs hardcoded

- Configurable from `.mac`:
    - Which ntuples are active (`/analysis/ntuple/setActivation`).
    - Source setup (`/gun/*`).
    - Event count (`/run/beamOn`).
    - Detector geometry/material/reflector setup (`/opnovice2/detector/*`).
- Hardcoded in current C++:
    - Several write switches in `SteppingAction` (`status`, `abs_spectrum`, `scint_spectrum`, `theta`).
    - Depth-slice boundaries (`counts_0..counts_9`).
    - Some fill paths currently commented out.

## Practical interpretation notes

- "Not written" can mean:
    1. ntuple not activated in macro,
    2. code path never reached physically in that run,
    3. code path disabled by hardcoded switch,
    4. fill lines are commented out.
- "Written but zero" usually means data row exists but the corresponding process did not occur, or the calculation path is incomplete (for example `scint_depth` currently).

## Update (2026-05-08): ntuple write-path fixes

The following paths were enabled/fixed in code:

- Ntuple 1 (`absorption`) fill is active again.
- Ntuple 2 (`scintillation`) fill is active again.
- Ntuple 4 (`abs_sp`) fill is active again.
- Ntuple 5 boundary-status counters are active again.
- Ntuple 7 (`scint_depth_std`) fill is active again.
- Ntuple 8 (`scat_angles`) fill is active again for qualifying Compton steps.
- Ntuple 6 (`pr_int`) now writes `energy_track` in the same row (column-fill order fixed).
- Ntuple 3 (`scint_depth`) now uses a valid mean-depth update path (no `NaN`).

Operational side effects observed during validation:

- Runtime increase is significant when all ntuples are active (high I/O cost).
- Output size increase is significant, especially for per-photon ntuples (for example `absorption`, `scintillation`, `abs_sp`).
- This is expected behavior; users should activate only the ntuples needed for a given study.

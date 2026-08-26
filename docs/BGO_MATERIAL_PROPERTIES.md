# BGO material-property choices

This note records the preliminary BGO (`Bi4Ge3O12`) constants implemented for `/opnovice2/detector/setDetectorMaterial 3`.

## Implemented values

| Property | Implemented value | Source / note |
| --- | --- | --- |
| Chemical formula | `Bi4Ge3O12`, undoped | Miller et al. list BGO as `Bi4Ge3O12` in their Geant4 scintillator material table. |
| Density | `7.13 g/cm3` | Miller et al., Table I, citing Mao, Zhang, and Zhu. |
| State / temperature | solid, `293.15 K` | Room-temperature solid default for this project. Miller et al. ran their measurements at `20 C`. |
| Emission spectrum | 25-point normalized energy-density spectrum peaking at `2.55 eV` (`486 nm`) | Derived from the 1001-value, machine-readable BGO wavelength distribution (`BGO_pr`) bundled in the UC Davis LUT Davis Model. This replaces the previous figure digitization. |
| Refractive index | constant `n = 2.15` over the BGO emission grid | Approximated from Miller et al., Fig. 8a and the BGO references used there. |
| Optical absorption length | constant `4 m` over the optical grid | User-selected preliminary value. Valenciaga et al. also used a `4.0 m` BGO optical absorption length in a peer-reviewed GATE optical-transport study. This is optical-photon bulk absorption, not gamma attenuation. |
| Light yield | `8500 photons/MeV` (`8.5 photons/keV`) | Miller et al., Table I, citing Moszynski et al., "Absolute light output of scintillators". |
| Decay time | `317 ns`, single component, `100%` fraction | Miller et al., Table I, citing EPIC Crystal BGO data. |
| Resolution scale | `1.0` | User-requested preliminary value. Miller et al. used `3.80` at 662 keV, but this implementation intentionally leaves the existing project convention unchanged. |
| Rise time | omitted | User-requested preliminary simplification. |
| Rayleigh scattering length | omitted | User-requested preliminary simplification. Gamma Rayleigh remains automatic through the Geant4 EM physics and BGO composition/density. |
| Crystal surface / reflector | existing project surfaces and constant reflector spectrum | User-requested same-as-existing treatment. |
| Optical coupling / SiPM response | no optical-coupling material added; existing SiPM table unchanged | User requested that SiPM response not be touched and that optical photons be counted without wavelength-dependent PDE. |

## Emission-data access and conversion

The replacement emission source is public numerical data rather than values read from a plot. The peer-reviewed LUT Davis Model paper states that BGO emission spectra are included in the application's scintillator database. The corresponding public UC Davis GitHub repository contains installers for Windows, Ubuntu, and macOS.

The easiest way to inspect the numerical data without installing MATLAB Runtime is:

1. Download `LUTDavisModelInstaller_MacOS.app.zip` from the repository. It is an ordinary ZIP archive and can be opened on any platform.
2. Open `Contents/Resources/bundle.zip` inside it.
3. Extract `application/LUTDavisModel.app/Contents/Resources/LUTDavisModel_mcr/LUTDavisMode/CrystalDatabase/BGO/Spectrum.mat`.
4. Load the MATLAB file with, for example, `scipy.io.loadmat`. It contains `BGO_pr`, an ascending vector of 1001 wavelength samples from `382.7 nm` to `650.0 nm`. The LUT application describes this input as an emission-spectrum distribution vector; the conversion here therefore treats its entries as equal-weight wavelength samples.

For the Geant4 table, each wavelength was converted with `E[eV] = 1239.841984 / wavelength[nm]`. The resulting energies were histogrammed into bins whose boundaries are the midpoints of the existing 25 energy nodes. Counts were divided by each bin width to obtain spectral density per eV and normalized to a maximum of one. This is necessary because Geant4 integrates the component values over photon energy; merely relabelling wavelength-spectrum values as energies would distort the sampled spectrum.

The public file does not embed a citation to the original BGO measurement, crystal batch, or measurement temperature. It is therefore a reproducible secondary database source, not a fully documented primary measurement. It is substantially more auditable than digitizing a plotted curve, but that missing primary provenance remains the main uncertainty in the emission model.

## Proportional light-yield choice

The BGO implementation intentionally remains proportional: Geant4 creates scintillation photons from deposited energy using the constant `8500 photons/MeV` yield. No Birks constant, particle-dependent yield, or other nonproportionality correction is applied, matching the user's decision and the current treatment of the other supported scintillators.

## Validation of the finalized preliminary choices

On 2026-08-26 the project was rebuilt and the supplied 1000-event validation macro was rerun with the machine-readable emission spectrum and constant `4 m` absorption length:

```text
bash scripts/build_app.sh
OPNOVICE_DATA_DIR=data/bgo_validation_1000_662keV_4m \
  bash scripts/run_batch.sh scripts/macros/bgo_662keV_1000_nt_absorption.mac
```

Geant4 11.4.1 completed all `1000` primary `662 keV` gamma events. It created `2,072,128` scintillation photons; `2,009,925` were absorbed in SiPM volumes and `13,597` were absorbed in the BGO. The SiPM absorption ntuple contains exactly `2,009,925` data rows. `scripts/generate_heatmap_csv.py` and `scripts/plot_heatmap_csv.py` were then used to produce a `480 x 480` heatmap under `data/bgo_validation_1000_662keV_4m/heatmaps/`.

## Sources

- L. Miller, A. Chapman, K. Auchettl, J. M. C. Brown, "Material Properties of Popular Radiation Detection Scintillator Crystals for Optical Physics Transport Modelling in Geant4", arXiv:2403.02668, especially Table I and Fig. 8a: https://arxiv.org/pdf/2403.02668
- C. Trigila, E. Moghe, E. Roncali, "Technical Note: Standalone application to generate custom reflectance Look-Up Table for advanced optical Monte Carlo simulation in GATE/Geant4", Medical Physics 48 (2021) 2800-2810, DOI 10.1002/mp.14863: https://pmc.ncbi.nlm.nih.gov/articles/PMC8547774/
- UC Davis Roncali Lab, public LUT Davis Model installer repository containing the machine-readable BGO spectrum: https://github.com/roncalilab/lut-davis-installer
- Y. Valenciaga, D. L. Prout, R. Taschereau, A. F. Chatziioannou, "Feasibility of Using Crystal Geometry for a DOI Scintillation Detector", IEEE Transactions on Radiation and Plasma Medical Sciences 2 (2018) 161-169, DOI 10.1109/TRPMS.2017.2760857: https://pmc.ncbi.nlm.nih.gov/articles/PMC6516480/

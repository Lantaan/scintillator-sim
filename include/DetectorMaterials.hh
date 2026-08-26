//
// Created by oslick on 03.06.2021.
//

#ifndef OPNOVICE2_DETECTROMATERIALS_HH
#define OPNOVICE2_DETECTROMATERIALS_HH

#endif //OPNOVICE2_DETECTROMATERIALS_HH

#include "DetectorConstruction.hh"
#include "G4Material.hh"
#include "G4Element.hh"
#include "G4NistManager.hh"



// Add all materials:

G4NistManager* man = G4NistManager::Instance();
G4Material* Si  =     man->FindOrBuildMaterial("G4_Si");
G4Material* Al  =     man->FindOrBuildMaterial("G4_Al");

// The elements we need to build complexe materials

G4Element* elCe   = man->FindOrBuildElement("Ce");
G4Element* elBr   = man->FindOrBuildElement("Br");
G4Element* elC    = man->FindOrBuildElement("C");
G4Element* elF    = man->FindOrBuildElement("F");
G4Element* elAl    = man->FindOrBuildElement("Al");
G4Element* elCs    = man->FindOrBuildElement("Cs");
G4Element* elI    = man->FindOrBuildElement("I");
G4Element* elTl    = man->FindOrBuildElement("Tl");
G4Element* elNa    = man->FindOrBuildElement("Na");
G4Element* elBi    = man->FindOrBuildElement("Bi");
G4Element* elGe    = man->FindOrBuildElement("Ge");
G4Element* elO     = man->FindOrBuildElement("O");

G4Material* CeBr_3;
G4Material* CsI;
G4Material* CsI_Tl;
G4Material* NaI;
G4Material* NaI_Tl;
G4Material* BGO;


G4Material* Vacuum;
G4Material* C2F4;

const G4int nEntries = 25;

// CsI optical properties
G4double PhotonEnergyCsI[nEntries] = {1.77 * eV, 1.80 * eV, 1.84 * eV, 1.88 * eV,
                                    1.91*eV, 1.93*eV, 1.98*eV, 2.02*eV, 2.07*eV,
                                    2.11*eV, 2.16*eV, 2.20*eV, 2.25*eV, 2.28*eV,
                                    2.36*eV, 2.45*eV, 2.48*eV, 2.55*eV, 2.61*eV,
                                    2.67*eV, 2.76*eV, 2.85*eV, 2.97*eV, 3.10*eV, 3.31*eV};

// relative scintillator yield
G4double FastCompCsI[nEntries] =     {0.15, 0.2, 0.23, 0.29,
                                        0.36, 0.4, 0.53, 0.6, 0.7,
                                        0.8, 0.85, 0.93, 0.975, 0.988,
                                        0.92, 0.8, 0.72, 0.6, 0.44,
                                        0.4, 0.27, 0.2, 0.15, 0.12, 0.05};

G4double rIndexCsI[nEntries] =       {1.79, 1.79, 1.79, 1.79,
                                        1.79, 1.79, 1.79, 1.79, 1.79,
                                        1.79, 1.79, 1.79, 1.79, 1.79,
                                        1.79, 1.79, 1.79, 1.79, 1.79,
                                        1.79, 1.79, 1.79, 1.79, 1.79, 1.79};
// Absorption length = Attenuation length
G4double AbsorptionCsI[nEntries] =   {420*mm, 410*mm, 400*mm, 395*mm,
                                        390*mm, 387*mm, 380*mm, 370*mm, 365*mm,
                                        360*mm, 350*mm, 345*mm, 340*mm, 338*mm,
                                        330*mm, 310*mm, 305*mm, 300*mm, 293*mm,
                                        287*mm, 275*mm, 270*mm, 255*mm, 245*mm, 225*mm};

// CeBr3 optical properties
G4double PhotonEnergyCeBr3[nEntries] = {2.86 * eV, 2.92 * eV, 2.95 * eV, 2.97 * eV,
                                   3.00*eV, 3.03*eV, 3.06*eV, 3.09*eV, 3.12*eV,
                                   3.16*eV, 3.19*eV, 3.22*eV, 3.25*eV, 3.29*eV,
                                   3.32*eV, 3.35*eV, 3.36*eV, 3.40*eV, 3.42*eV,
                                   3.43*eV, 3.44*eV, 3.48*eV, 3.52*eV, 3.56*eV, 3.60*eV};

// relative scintillator yield
G4double FastCompCeBr3[nEntries] =     {0.010, 0.031, 0.061, 0.122,
                                        0.184, 0.245, 0.408, 0.551, 0.673,
                                        0.796, 0.816, 0.837, 0.857, 0.898,
                                        0.980, 1.000, 0.959, 0.816, 0.653,
                                        0.571, 0.408, 0.224, 0.143, 0.082, 0.020};

G4double rIndexCeBr3[nEntries] =       {1.9, 1.9, 1.9, 1.9,
                                        1.9, 1.9, 1.9, 1.9, 1.9,
                                        1.9, 1.9, 1.9, 1.9, 1.9,
                                        1.9, 1.9, 1.9, 1.9, 1.9,
                                        1.9, 1.9, 1.9, 1.9, 1.9, 1.9};

// Absorption length = Attenuation length
G4double AbsorptionCeBr3[nEntries] =   {155*mm, 150*mm, 147*mm, 145*mm,
                                   143*mm, 141*mm, 140*mm, 135*mm, 133*mm,
                                   130*mm, 129*mm, 126*mm, 125*mm, 121*mm,
                                   120*mm, 117*mm, 116*mm, 115*mm, 114*mm,
                                   113*mm, 112*mm, 110*mm, 108*mm, 106*mm, 105*mm};


// NaI optical properties
G4double PhotonEnergyNaI[nEntries] = {2.25 * eV, 2.30 * eV, 2.34 * eV, 2.38 * eV,
                                      2.43*eV, 2.48*eV, 2.56*eV, 2.58*eV, 2.64*eV,
                                      2.70*eV, 2.76*eV, 2.82*eV, 2.88*eV, 2.95*eV,
                                      2.99*eV, 3.10*eV, 3.18*eV, 3.22*eV, 3.37*eV,
                                      3.44*eV, 3.54*eV, 3.63*eV, 3.76*eV, 3.88*eV, 3.94*eV};

// relative scintillator yield
G4double FastCompNaI[nEntries] =     {0, 0.025, 0.06, 0.075,
                                      0.12, 0.15, 0.2, 0.31, 0.4,
                                      0.6, 0.73, 0.8, 0.95, 0.97,
                                      0.987, 0.945, 0.89, 0.8, 0.6,
                                      0.48, 0.425, 0.4, 0.2, 0.025, 0};

G4double rIndexNaI[nEntries] =       {1.85, 1.85, 1.85, 1.85,
                                      1.85, 1.85, 1.85, 1.85, 1.85,
                                      1.85, 1.85, 1.85, 1.85, 1.85,
                                      1.85, 1.85, 1.85, 1.85, 1.85,
                                      1.85, 1.85, 1.85, 1.85, 1.85, 1.85};
// Absorption length = Attenuation length
G4double AbsorptionNaI[nEntries] =   {429*mm, 429*mm, 429*mm, 429*mm,
                                      429*mm, 429*mm, 429*mm, 429*mm, 429*mm,
                                      429*mm, 429*mm, 429*mm, 429*mm, 429*mm,
                                      429*mm, 429*mm, 429*mm, 429*mm, 429*mm,
                                      429*mm, 429*mm, 429*mm, 429*mm, 429*mm, 429*mm};

// BGO (Bi4Ge3O12) optical properties.
// The emission shape is derived from the machine-readable BGO wavelength
// distribution bundled with the UC Davis LUT Davis Model. The 1001 wavelengths
// were converted to photon energy, binned on this grid, divided by bin width,
// and normalized to a peak value of one.
G4double PhotonEnergyBGO[nEntries] = {1.80 * eV, 1.90 * eV, 2.00 * eV, 2.10 * eV,
                                      2.20 * eV, 2.30 * eV, 2.40 * eV, 2.50 * eV,
                                      2.55 * eV, 2.60 * eV, 2.65 * eV, 2.70 * eV,
                                      2.80 * eV, 2.90 * eV, 3.00 * eV, 3.10 * eV,
                                      3.20 * eV, 3.30 * eV, 3.40 * eV, 3.50 * eV,
                                      3.60 * eV, 3.70 * eV, 3.80 * eV, 3.90 * eV,
                                      4.00 * eV};

// Relative scintillation spectral density per unit photon energy.
G4double FastCompBGO[nEntries] =     {0.000, 0.069, 0.277, 0.454,
                                      0.662, 0.831, 0.962, 0.985, 1.000,
                                      0.954, 0.908, 0.810, 0.662, 0.485,
                                      0.292, 0.169, 0.062, 0.000, 0.000,
                                      0.000, 0.000, 0.000, 0.000, 0.000, 0.000};

G4double rIndexBGO[nEntries] =       {2.15, 2.15, 2.15, 2.15,
                                      2.15, 2.15, 2.15, 2.15, 2.15,
                                      2.15, 2.15, 2.15, 2.15, 2.15,
                                      2.15, 2.15, 2.15, 2.15, 2.15,
                                      2.15, 2.15, 2.15, 2.15, 2.15, 2.15};

// Constant bulk optical absorption length adopted for the preliminary model.
G4double AbsorptionBGO[nEntries] =   {4*m, 4*m, 4*m, 4*m,
                                      4*m, 4*m, 4*m, 4*m, 4*m,
                                      4*m, 4*m, 4*m, 4*m, 4*m,
                                      4*m, 4*m, 4*m, 4*m, 4*m,
                                      4*m, 4*m, 4*m, 4*m, 4*m, 4*m};

// Reflector optical properties

G4double rIndex_ref[nEntries] =       {1.35, 1.35, 1.35, 1.35,
                                       1.35, 1.35, 1.35, 1.35, 1.35,
                                       1.35, 1.35, 1.35, 1.35, 1.35,
                                       1.35, 1.35, 1.35, 1.35, 1.35,
                                       1.35, 1.35, 1.35, 1.35, 1.35, 1.35};

// SiPM optical properties

//  G4double rIndex_SiPM[nEntries] =       {1.35, 1.35, 1.35, 1.35,
//                                  1.35, 1.35, 1.35, 1.35, 1.35,
//                                  1.35, 1.35, 1.35, 1.35, 1.35,
//                                  1.35, 1.35, 1.35, 1.35, 1.35,
//                                  1.35, 1.35, 1.35, 1.35, 1.35, 1.35};


G4double Absorption_SiPM[nEntries] =   {0.001*mm, 0.001*mm, 0.001*mm, 0.001*mm, 0.001*mm,
                                        0.001*mm, 0.001*mm, 0.001*mm, 0.001*mm, 0.001*mm,
                                        0.001*mm, 0.001*mm, 0.001*mm, 0.001*mm, 0.001*mm,
                                        0.001*mm, 0.001*mm, 0.001*mm, 0.001*mm, 0.001*mm,
                                        0.001*mm, 0.001*mm, 0.001*mm, 0.001*mm, 0.001*mm};

// World optical properties
G4double rIndex_air[nEntries] =       { 1.0003, 1.0003, 1.0003, 1.0003,
                                        1.0003, 1.0003, 1.0003, 1.0003, 1.0003,
                                        1.0003, 1.0003, 1.0003, 1.0003, 1.0003,
                                        1.0003, 1.0003, 1.0003, 1.0003, 1.0003,
                                        1.0003, 1.0003, 1.0003, 1.0003, 1.0003, 1.0003};




G4double reflectivity[nEntries]=      { 0.97, 0.97, 0.97, 0.97, 0.97,
                                        0.97, 0.97, 0.97, 0.97, 0.97,
                                        0.97, 0.97, 0.97, 0.97, 0.97,
                                        0.97, 0.97, 0.97, 0.97, 0.97,
                                        0.97, 0.97, 0.97, 0.97, 0.97};


G4double SpSp[nEntries]=       	{1.0, 1.0, 1.0, 1.0, 1.0,
                                 1.0, 1.0, 1.0, 1.0, 1.0,
                                 1.0, 1.0, 1.0, 1.0, 1.0,
                                 1.0, 1.0, 1.0, 1.0, 1.0,
                                 1.0, 1.0, 1.0, 1.0, 1.0};


// Scintillator - SiPM surface   ***************************************************************************

//    G4OpticalSurface* Sc_SiPM = new G4OpticalSurface("Sc_SiPM");

//    G4LogicalBorderSurface* Sc_SiPM_log = new G4LogicalBorderSurface("Sc_SiPM", fScintillator, fSiPMXY, Sc_SiPM);

//    Sc_SiPM->SetType(dielectric_dielectric);
//    Sc_SiPM->SetModel(unified);
//    Sc_SiPM->SetFinish(polished);



//    G4double reflectivity_SiPM[nEntries]=      { 1.0, 1.0, 1.0, 1.0,
//                                            1.0, 1.0, 1.0, 1.0,
//                                            1.0, 1.0, 1.0, 1.0,
//                                            1.0, 1.0, 1.0, 1.0,
//                                            1.0, 1.0, 1.0, 1.0, 1.0};


//    fSc_SiPMMPT->AddProperty("REFLECTIVITY", PhotonEnergyCeBr3, reflectivity_SiPM, nEntries);
//   fSc_SiPMMPT->AddProperty("RINDEX", PhotonEnergyCeBr3, rIndex, nEntries);

//    Sc_SiPM->SetMaterialPropertiesTable(fSc_SiPMMPT);


// SiPM - Reflector surface             *************************************************+

//    G4OpticalSurface* Si_Ref = new G4OpticalSurface("Si_Ref");

//    G4LogicalBorderSurface* Si_Ref_log      = new G4LogicalBorderSurface("Si_Ref", fSiPMXY, fReflector, Si_Ref);
//    G4LogicalBorderSurface* Si_Ref_log_11      = new G4LogicalBorderSurface("Si_Ref", fSiPMXY, fReflectorYZ1, Si_Ref);
//    G4LogicalBorderSurface* Si_Ref_log_12      = new G4LogicalBorderSurface("Si_Ref", fSiPMXY, fReflectorYZ2, Si_Ref);
//    G4LogicalBorderSurface* Si_Ref_log_21      = new G4LogicalBorderSurface("Si_Ref", fSiPMXY, fReflectorXZ1, Si_Ref);
//    G4LogicalBorderSurface* Si_Ref_log_22      = new G4LogicalBorderSurface("Si_Ref", fSiPMXY, fReflectorXZ2, Si_Ref);

//    Si_Ref->SetType(dielectric_dielectric);
//    Si_Ref->SetModel(unified);
//    Si_Ref->SetFinish(groundbackpainted);
//    Si_Ref->SetSigmaAlpha(0.0);

//    fSi_RefMPT->AddProperty("REFLECTIVITY", PhotonEnergyCeBr3, reflectivity, nEntries);
//    fSi_RefMPT->AddProperty("RINDEX", PhotonEnergyCeBr3, rIndex, nEntries);
//    fSi_RefMPT->AddProperty("LAMBERTIAN", PhotonEnergyCeBr3, SpSp, nEntries);
//    Si_Ref->SetMaterialPropertiesTable(fSi_RefMPT);

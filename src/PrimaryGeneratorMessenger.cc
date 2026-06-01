//
// ********************************************************************
// * License and Disclaimer                                           *
// *                                                                  *
// * The  Geant4 software  is  copyright of the Copyright Holders  of *
// * the Geant4 Collaboration.  It is provided  under  the terms  and *
// * conditions of the Geant4 Software License,  included in the file *
// * LICENSE and available at  http://cern.ch/geant4/license .  These *
// * include a list of copyright holders.                             *
// *                                                                  *
// * Neither the authors of this software system, nor their employing *
// * institutes,nor the agencies providing financial support for this *
// * work  make  any representation or  warranty, express or implied, *
// * regarding  this  software system or assume any liability for its *
// * use.  Please see the license in the file  LICENSE  and URL above *
// * for the full disclaimer and the limitation of liability.         *
// *                                                                  *
// * This  code  implementation is the result of  the  scientific and *
// * technical work of the GEANT4 collaboration.                      *
// * By using,  copying,  modifying or  distributing the software (or *
// * any work based  on the software)  you  agree  to acknowledge its *
// * use  in  resulting  scientific  publications,  and indicate your *
// * acceptance of all terms of the Geant4 Software license.          *
// ********************************************************************
//
/// \file optical/OpNovice2/src/PrimaryGeneratorMessenger.cc
/// \brief Implementation of the PrimaryGeneratorMessenger class
//
//
//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

#include "PrimaryGeneratorMessenger.hh"

#include "PrimaryGeneratorAction.hh"
#include "G4UIdirectory.hh"
#include "G4UIcmdWithADoubleAndUnit.hh"
#include "G4UIcmdWithAString.hh"
#include "G4SystemOfUnits.hh"

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

PrimaryGeneratorMessenger::
  PrimaryGeneratorMessenger(PrimaryGeneratorAction* Gun)
  : G4UImessenger(),
    fPrimaryAction(Gun)
{
  fGunDir = new G4UIdirectory("/opnovice2/gun/");
  fGunDir->SetGuidance("PrimaryGenerator control");

  fPolarCmd =
           new G4UIcmdWithADoubleAndUnit("/opnovice2/gun/optPhotonPolar",this);
  fPolarCmd->SetGuidance("Set linear polarization");
  fPolarCmd->SetGuidance("  angle w.r.t. (k,n) plane");
  fPolarCmd->SetParameterName("angle",true);
  fPolarCmd->SetUnitCategory("Angle");
  fPolarCmd->SetDefaultValue(-360.0);
  fPolarCmd->SetDefaultUnit("deg");
  fPolarCmd->AvailableForStates(G4State_Idle);

  SetGunAngle=
          new G4UIcmdWithADoubleAndUnit("/opnovice2/gun/gunAngleToZAxis",this);
  SetGunAngle->SetGuidance("Set angle of shooting direction");
  SetGunAngle->SetGuidance("  to z axis");
  SetGunAngle->SetParameterName("dir_angle",true);
  SetGunAngle->SetUnitCategory("Angle");
  SetGunAngle->SetDefaultValue(0.0);
  SetGunAngle->SetDefaultUnit("deg");
  SetGunAngle->AvailableForStates(G4State_Idle, G4State_PreInit);

  SetBeamType = new G4UIcmdWithAString("/opnovice2/gun/beamType", this);
  SetBeamType->SetGuidance("Set beam profile type.");
  SetBeamType->SetGuidance("Available values: point, disk, gauss.");
  SetBeamType->SetParameterName("beam_type", false);
  SetBeamType->AvailableForStates(G4State_Idle, G4State_PreInit);

  SetBeamSize = new G4UIcmdWithADoubleAndUnit("/opnovice2/gun/beamSize", this);
  SetBeamSize->SetGuidance("Set beam size in the plane perpendicular to the beam direction.");
  SetBeamSize->SetGuidance("For beamType=disk, this is disk radius.");
  SetBeamSize->SetGuidance("For beamType=gauss, this is Gaussian half-width at half maximum.");
  SetBeamSize->SetParameterName("beam_size", false);
  SetBeamSize->SetUnitCategory("Length");
  SetBeamSize->SetDefaultValue(0.0);
  SetBeamSize->SetDefaultUnit("mm");
  SetBeamSize->AvailableForStates(G4State_Idle, G4State_PreInit);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

PrimaryGeneratorMessenger::~PrimaryGeneratorMessenger()
{
  delete fPolarCmd;
  delete SetGunAngle;
  delete SetBeamType;
  delete SetBeamSize;
  delete fGunDir;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void PrimaryGeneratorMessenger::SetNewValue(
                                        G4UIcommand* command, G4String newValue)
{
  if (command == fPolarCmd) {
    G4double angle;
    angle = fPolarCmd->GetNewDoubleValue(newValue);
      if (angle == -360.0*deg) {
         fPrimaryAction->SetOptPhotonPolar();
      } else {
         fPrimaryAction->SetOptPhotonPolar(angle);
      }
  }
  if (command == SetGunAngle) {
    G4double dir_angle;
    dir_angle = SetGunAngle->GetNewDoubleValue(newValue);
    fPrimaryAction->SetGunAngleDir(dir_angle);
  }
  if (command == SetBeamType) {
    if (newValue == "point") {
      fPrimaryAction->SetBeamProfileType(PrimaryGeneratorAction::kBeamPoint);
    }
    else if (newValue == "disk") {
      fPrimaryAction->SetBeamProfileType(PrimaryGeneratorAction::kBeamDisk);
    }
    else if (newValue == "gauss") {
      fPrimaryAction->SetBeamProfileType(PrimaryGeneratorAction::kBeamGauss);
    }
    else {
      G4ExceptionDescription ed;
      ed << "Invalid beam type: " << newValue
         << ". Available values are: point, disk, gauss.";
      G4Exception("PrimaryGeneratorMessenger", "OpNovice2_005", FatalException, ed);
    }
  }
  if (command == SetBeamSize) {
    const G4double size = SetBeamSize->GetNewDoubleValue(newValue);
    fPrimaryAction->SetBeamProfileSize(size);
  }
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

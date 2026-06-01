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
/// \file optical/OpNovice2/src/PrimaryGeneratorAction.cc
/// \brief Implementation of the PrimaryGeneratorAction class
//
//
//
//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

#include "PrimaryGeneratorAction.hh"
#include "PrimaryGeneratorMessenger.hh"

#include "DetectorConstruction.hh"
#include <cmath>
#include "Randomize.hh"
#include "G4PhysicalConstants.hh"

#include "G4Event.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4ParticleDefinition.hh"

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

PrimaryGeneratorAction::PrimaryGeneratorAction(DetectorConstruction* detector)
 : G4VUserPrimaryGeneratorAction(),
   fParticleGun(nullptr),
   fDetector(detector),
   fBeamProfileType(kBeamPoint),
   fBeamProfileSize(0.0 * mm)
{
  G4int n_particle = 1;
  fParticleGun = new G4ParticleGun(n_particle);

  //create a messenger for this class
  fGunMessenger = new PrimaryGeneratorMessenger(this);

  //default kinematic
  //
  G4ParticleTable* particleTable = G4ParticleTable::GetParticleTable();
  G4ParticleDefinition* particle = particleTable->FindParticle("gamma");

  fParticleGun->SetParticleDefinition(particle);
  fParticleGun->SetParticleTime(0.0*ns);

//  fParticleGun->SetParticleEnergy(1*MeV);

  G4double fGun_z= fDetector->GetTotalThickness() + 0.1 *mm;
  fParticleGun->SetParticlePosition(G4ThreeVector(0 *cm,0 *cm, -fGun_z));

  fParticleGun->SetParticleMomentumDirection(G4ThreeVector(0.,0.,1.));

}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

PrimaryGeneratorAction::~PrimaryGeneratorAction()
{
  delete fParticleGun;
  delete fGunMessenger;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void PrimaryGeneratorAction::GeneratePrimaries(G4Event* anEvent)
{
  const G4ThreeVector basePosition = fParticleGun->GetParticlePosition();
  const G4ThreeVector offset = SampleTransverseOffset();
  if (offset.mag2() > 0.0) {
    fParticleGun->SetParticlePosition(basePosition + offset);
  }

  fParticleGun->GeneratePrimaryVertex(anEvent);

  if (offset.mag2() > 0.0) {
    fParticleGun->SetParticlePosition(basePosition);
  }
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void PrimaryGeneratorAction::SetGunAngleDir(G4double angle)
{
  G4double x_dir = tan(angle);
  fParticleGun->SetParticleMomentumDirection(G4ThreeVector(x_dir, 0. ,1.));
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void PrimaryGeneratorAction::SetBeamProfileType(BeamProfileType type)
{
  fBeamProfileType = type;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void PrimaryGeneratorAction::SetBeamProfileSize(G4double size)
{
  fBeamProfileSize = (size >= 0.0) ? size : 0.0;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void PrimaryGeneratorAction::BuildTransverseBasis(const G4ThreeVector& direction,
                                                   G4ThreeVector& e1,
                                                   G4ThreeVector& e2) const
{
  G4ThreeVector dir = direction;
  if (dir.mag2() <= 0.0) {
    dir = G4ThreeVector(0.0, 0.0, 1.0);
  }
  dir = dir.unit();

  G4ThreeVector helper = (std::fabs(dir.z()) < 0.9)
    ? G4ThreeVector(0.0, 0.0, 1.0)
    : G4ThreeVector(0.0, 1.0, 0.0);

  e1 = dir.cross(helper);
  if (e1.mag2() <= 0.0) {
    helper = G4ThreeVector(1.0, 0.0, 0.0);
    e1 = dir.cross(helper);
  }
  e1 = e1.unit();
  e2 = dir.cross(e1).unit();
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

G4ThreeVector PrimaryGeneratorAction::SampleTransverseOffset() const
{
  if (fBeamProfileType == kBeamPoint || fBeamProfileSize <= 0.0) {
    return G4ThreeVector();
  }

  G4double localX = 0.0;
  G4double localY = 0.0;

  if (fBeamProfileType == kBeamDisk) {
    const G4double r = fBeamProfileSize * std::sqrt(G4UniformRand());
    const G4double phi = twopi * G4UniformRand();
    localX = r * std::cos(phi);
    localY = r * std::sin(phi);
  }
  else if (fBeamProfileType == kBeamGauss) {
    const G4double sigma = fBeamProfileSize / std::sqrt(2.0 * std::log(2.0));
    localX = G4RandGauss::shoot(0.0, sigma);
    localY = G4RandGauss::shoot(0.0, sigma);
  }

  G4ThreeVector e1;
  G4ThreeVector e2;
  BuildTransverseBasis(fParticleGun->GetParticleMomentumDirection(), e1, e2);
  return localX * e1 + localY * e2;
}


//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void PrimaryGeneratorAction::SetOptPhotonPolar()
{
 G4double angle = G4UniformRand() * 360.0*deg;
 SetOptPhotonPolar(angle);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

void PrimaryGeneratorAction::SetOptPhotonPolar(G4double angle)
{
 if (fParticleGun->GetParticleDefinition()->GetParticleName()!="opticalphoton")
   {
     G4cout << "--> warning from PrimaryGeneratorAction::SetOptPhotonPolar() :"
               "the particleGun is not an opticalphoton" << G4endl;
     return;
   }

 G4ThreeVector normal (1., 0., 0.);
 G4ThreeVector kphoton = fParticleGun->GetParticleMomentumDirection();
 G4ThreeVector product = normal.cross(kphoton);
 G4double modul2       = product*product;

 G4ThreeVector e_perpend (0., 0., 1.);
 if (modul2 > 0.) e_perpend = (1./std::sqrt(modul2))*product;
 G4ThreeVector e_paralle    = e_perpend.cross(kphoton);

 G4ThreeVector polar = std::cos(angle)*e_paralle + std::sin(angle)*e_perpend;
 fParticleGun->SetParticlePolarization(polar);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

#----------------------------------------------------------------------------
# Setup the project
cmake_minimum_required(VERSION 2.6 FATAL_ERROR)
project(OpNovice2)

#----------------------------------------------------------------------------
# Find Geant4 package, activating all available UI and Vis drivers by default
# You can set WITH_GEANT4_UIVIS to OFF via the command line or ccmake/cmake-gui
# to build a batch mode only executable
#
option(WITH_GEANT4_UIVIS "Build example with Geant4 UI and Vis drivers" ON)
if(WITH_GEANT4_UIVIS)
  find_package(Geant4 REQUIRED ui_all vis_all)
else()
  find_package(Geant4 REQUIRED)
endif()

#----------------------------------------------------------------------------
# Setup Geant4 include directories and compile definitions
#
include(${Geant4_USE_FILE})

#----------------------------------------------------------------------------
# Locate sources and headers for this project
#
include_directories(${PROJECT_SOURCE_DIR}/include 
                    ${Geant4_INCLUDE_DIR})
file(GLOB sources ${PROJECT_SOURCE_DIR}/src/*.cc)
file(GLOB headers ${PROJECT_SOURCE_DIR}/include/*.hh)
file(GLOB inputs ${PROJECT_SOURCE_DIR}/*.in)
file(GLOB macros ${PROJECT_SOURCE_DIR}/*.mac)

#----------------------------------------------------------------------------
# Add the executable, and link it to the Geant4 libraries
#
add_executable(OpNovice2 OpNovice2.cc ${sources} ${headers} include/DetectorMaterials.hh)
# Work around broken libG4visQt3D builds on some environments (WSL/driver/toolchain
# combinations) while keeping Qt/OpenGL UI support.
set(OPNOVICE2_GEANT4_LIBRARIES "")
foreach(_g4lib ${Geant4_LIBRARIES})
  if(NOT _g4lib MATCHES "G4visQt3D")
    list(APPEND OPNOVICE2_GEANT4_LIBRARIES ${_g4lib})
  endif()
endforeach()
target_link_libraries(OpNovice2 ${OPNOVICE2_GEANT4_LIBRARIES})

# Geant4 10.7 can advertise Qt3D through compile definitions even when the
# runtime/library is unusable on some systems. Undefine it for this target so
# G4VisExecutive does not reference G4Qt3D symbols.
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(OpNovice2 PRIVATE -UG4VIS_USE_QT3D)
endif()

#----------------------------------------------------------------------------
# Copy all scripts to the build directory, i.e. the directory in which we
# build OpNovice2. This is so that we can run the executable directly because it
# relies on these scripts being in the current working directory.
#
set(OpNovice2_SCRIPTS
        vis.mac
  )

foreach(_script ${OpNovice2_SCRIPTS})
  configure_file(
    ${PROJECT_SOURCE_DIR}/${_script}
    ${PROJECT_BINARY_DIR}/${_script}
    COPYONLY
    )
endforeach()

#----------------------------------------------------------------------------
# Install the executable to 'bin' directory under CMAKE_INSTALL_PREFIX
#
install(TARGETS OpNovice2 DESTINATION bin)


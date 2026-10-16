cmake_minimum_required(VERSION 3.10)

include(CheckIncludeFile)

project(surfit)

SET(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/bin)
SET(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/bin)
SET(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/cmake/")

# ----------------------------------
# what to build
# ----------------------------------
# A Python wheel wants only the engine and its bindings: no Tcl module, no CLI,
# no globe/freeflow, and every shared library installed *inside* the package so
# the extension finds it through $ORIGIN.

option(SURFIT_BUILD_TCL "Build the Tcl front end (module, CLI, globe, freeflow)" OFF)
option(SURFIT_BUILD_PYTHON "Build the Python bindings" ON)
option(SURFIT_PYTHON_WHEEL "Install for a Python wheel, inside the package" OFF)

if (SURFIT_PYTHON_WHEEL)
	set(SURFIT_LIBDIR "surfit")
else()
	set(SURFIT_LIBDIR "lib")
endif()
set(SURFIT_LIBDIR "${SURFIT_LIBDIR}" CACHE STRING
	"Install destination for the shared libraries")

# The engine has no Tcl dependency: StringMatch() is local and the logging
# speaks to stdio and to the log hook.  Tcl is needed only by the front end and
# by the plugins that wrap themselves as Tcl commands.
if (SURFIT_BUILD_TCL)
	find_package(TCL REQUIRED)
	find_package(SWIG REQUIRED)
	INCLUDE(${SWIG_USE_FILE})
	SET(CMAKE_SWIG_FLAGS "-c++")
	message(${SWIG_EXECUTABLE})
endif()

find_package(ZLIB)
find_package(JPEG)
find_package(NetCDF)

# sstuff uses pthreads through the bundled ptypes library.
find_package(Threads REQUIRED)

set(HAVE_THREADS 1)

# ----------------------------------
# projects
# ----------------------------------

#config
set(VERSION "3.1")
CHECK_INCLUDE_FILE(string.h  HAVE_STRING_H)
CHECK_INCLUDE_FILE(stdlib.h  HAVE_STDLIB_H)
CHECK_INCLUDE_FILE(unistd.h  HAVE_UNISTD_H)

if (JPEG_FOUND)
	SET(HAVE_LIBJPEG 1)
endif (JPEG_FOUND)

if (NETCDF_FOUND)
	SET(HAVE_NETCDF 1)
endif (NETCDF_FOUND)


configure_file(config.h.in config.h)


# Libraries
add_subdirectory(sstuff)
add_subdirectory(surfit)
add_subdirectory(surfit_io)

# Python bindings; skipped automatically when pybind11 is unavailable
if (SURFIT_BUILD_PYTHON)
	add_subdirectory(pysurfit)
endif()

if (SURFIT_BUILD_TCL)
	add_subdirectory(tclsurfit)

	if (ZLIB_FOUND)
		add_subdirectory(globe)
	endif(ZLIB_FOUND)

	add_subdirectory(freeflow)

	# Executabels
	add_subdirectory(surfit_cmd)
endif()


# uninstall target
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/cmake_uninstall.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake"
    IMMEDIATE @ONLY)

add_custom_target(uninstall
    COMMAND ${CMAKE_COMMAND} -P ${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake)


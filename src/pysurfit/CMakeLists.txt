# Python bindings (pybind11) for the surfit core.
#
# The extension is built *inside* the `surfit` package so the package stays
# relocatable, and the pure-Python part of that package is copied next to it
# from python/surfit.
#
# Optional: when pybind11 is absent the rest of the project still builds.
# Point CMake at it with
#   -Dpybind11_DIR=<prefix>/share/cmake/pybind11

find_package(pybind11 CONFIG QUIET)

if (NOT pybind11_FOUND)
	message(STATUS "pybind11 not found - skipping the Python bindings "
	               "(configure with -Dpybind11_DIR=<prefix>/share/cmake/pybind11)")
else()
	SET( PROJ_NAME _surfit )
	PROJECT( ${PROJ_NAME} )

	pybind11_add_module(${PROJ_NAME} MODULE src/module.cpp)

	include_directories(
		${CMAKE_CURRENT_SOURCE_DIR}/../surfit/src
		${CMAKE_CURRENT_SOURCE_DIR}/../surfit_io/src
		${CMAKE_CURRENT_SOURCE_DIR}/../sstuff/src
		${CMAKE_CURRENT_SOURCE_DIR}/../sstuff/src/ptypes
		${CMAKE_BINARY_DIR}
	)

	target_link_libraries(${PROJ_NAME} PRIVATE libsurfit_io libsstuff libsurfit)

	# The extension lives inside the package directory, one level below the
	# shared libraries it links against.
	set_target_properties( ${PROJ_NAME} PROPERTIES
		LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin/surfit"
		BUILD_RPATH "$ORIGIN/.."
		INSTALL_RPATH "$ORIGIN/.."
	)

	# Pure-Python part of the package.
	file(COPY "${CMAKE_CURRENT_SOURCE_DIR}/python/surfit"
	     DESTINATION "${CMAKE_BINARY_DIR}/bin")

	install(TARGETS ${PROJ_NAME} DESTINATION lib/surfit)
	install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/python/surfit"
	        DESTINATION lib)
endif()

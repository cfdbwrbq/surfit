# Python bindings (pybind11) for the surfit core.
#
# Optional: when pybind11 is not installed the rest of the project still
# builds.  Point CMake at it with
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
		${CMAKE_CURRENT_SOURCE_DIR}/../sstuff/src
		${CMAKE_CURRENT_SOURCE_DIR}/../sstuff/src/ptypes
		${CMAKE_BINARY_DIR}
	)

	target_link_libraries(${PROJ_NAME} PRIVATE libsstuff libsurfit)

	set_target_properties( ${PROJ_NAME} PROPERTIES
		LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
		BUILD_RPATH "$ORIGIN"
		INSTALL_RPATH "$ORIGIN"
	)

	install(TARGETS ${PROJ_NAME} DESTINATION lib)
endif()

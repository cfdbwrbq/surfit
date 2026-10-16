# Python bindings (pybind11) for the surfit core.
#
# The extension is built *inside* the `surfit` package so the package stays
# relocatable, and the pure-Python part of that package is copied next to it
# from python/surfit.
#
# Optional: when pybind11 is absent the rest of the project still builds.
# Point CMake at it with
#   -Dpybind11_DIR=<prefix>/share/cmake/pybind11
# When building through pip the build environment has pybind11 installed but its
# CMake config is not on the prefix path, so ask the interpreter for the path.

find_package(pybind11 CONFIG QUIET)

if (NOT pybind11_FOUND)
	find_package(Python COMPONENTS Interpreter QUIET)
	if (Python_Interpreter_FOUND)
		execute_process(
			COMMAND "${Python_EXECUTABLE}" -m pybind11 --cmakedir
			OUTPUT_VARIABLE SURFIT_PYBIND11_DIR
			OUTPUT_STRIP_TRAILING_WHITESPACE
			ERROR_QUIET)
		if (SURFIT_PYBIND11_DIR)
			set(pybind11_DIR "${SURFIT_PYBIND11_DIR}")
			find_package(pybind11 CONFIG QUIET)
		endif()
	endif()
endif()

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

	# In the build tree the extension sits one level below the libraries; in an
	# installed wheel every library lands in the same package directory.
	set_target_properties( ${PROJ_NAME} PROPERTIES
		LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin/surfit"
		BUILD_RPATH "$ORIGIN/.."
		INSTALL_RPATH "$ORIGIN"
	)

	# Pure-Python part of the package, next to the extension in the build tree.
	file(COPY "${CMAKE_CURRENT_SOURCE_DIR}/python/surfit"
	     DESTINATION "${CMAKE_BINARY_DIR}/bin")

	if (SURFIT_PYTHON_WHEEL)
		# scikit-build-core packs whatever CMake installs, so the libraries
		# installed into ${SURFIT_LIBDIR} (= surfit) end up inside the wheel.
		install(TARGETS ${PROJ_NAME} DESTINATION surfit)
		install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/python/surfit/"
		        DESTINATION surfit)
	endif()
endif()

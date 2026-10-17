# The freeflow library and, when the Tcl front end is built, its Tcl plugin.
#
# libfreeflow_core has no Tcl dependency at all.  freeflow_wrap.cxx is the
# pre-generated SWIG wrapper (SWIG 1.3.28, checked in); it is the Tcl plugin and
# is built as a separate module under the historical file name libfreeflow.so,
# so `load libfreeflow[info sharedlibextension]` keeps working.

SET( PROJ_NAME libfreeflow_core )

PROJECT( ${PROJ_NAME} )

FILE(GLOB_RECURSE srcs_cpp src/*.c*)
FILE(GLOB_RECURSE hdrs src/*.h*)

# The wrapper belongs to the plugin target below, not to the library.
list(REMOVE_ITEM srcs_cpp ${CMAKE_CURRENT_SOURCE_DIR}/src/freeflow_wrap.cxx)

set (INCL_DIRS src
	${CMAKE_BINARY_DIR}
	../sstuff/src
	../surfit/src
)

include_directories( ${INCL_DIRS} )

add_library(${PROJ_NAME} SHARED ${srcs_cpp} ${hdrs})

target_link_libraries(${PROJ_NAME} libsstuff libsurfit)

set_target_properties( ${PROJ_NAME} PROPERTIES PREFIX "" )

install(TARGETS ${PROJ_NAME} DESTINATION ${SURFIT_LIBDIR})

#
# the Tcl plugin, only when the Tcl front end is being built
#

if (SURFIT_BUILD_TCL)
	add_library(freeflow_tcl MODULE src/freeflow_wrap.cxx)

	target_include_directories(freeflow_tcl PRIVATE ${TCL_INCLUDE_PATH} ${INCL_DIRS})

	target_link_libraries(freeflow_tcl
		${PROJ_NAME}
		libsstuff
		libsurfit
		${TCL_LIBRARY}
	)

	set_target_properties(freeflow_tcl PROPERTIES
		PREFIX ""
		OUTPUT_NAME "libfreeflow"
		LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
	)

	install(TARGETS freeflow_tcl DESTINATION ${SURFIT_LIBDIR})
endif()

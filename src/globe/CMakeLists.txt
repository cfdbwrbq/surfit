# The DEM library and, when the Tcl front end is built, its Tcl plugin.
#
# libglobe_core has no Tcl dependency at all: the DEM code speaks to the engine
# and to the log, and nothing else.  globe_wrap.cxx is the pre-generated SWIG
# wrapper (SWIG 1.3.28, checked in); it is the Tcl plugin and is built as a
# separate module under the historical file name libglobe.so, so
# `load libglobe[info sharedlibextension]` in the examples keeps working.

SET( PROJ_NAME libglobe_core )

PROJECT( ${PROJ_NAME} )

FILE(GLOB_RECURSE srcs_cpp src/*.c*)
FILE(GLOB_RECURSE hdrs src/*.h*)

# The wrapper belongs to the plugin target below, not to the library.
list(REMOVE_ITEM srcs_cpp ${CMAKE_CURRENT_SOURCE_DIR}/src/globe_wrap.cxx)

set (INCL_DIRS src
	${CMAKE_BINARY_DIR}
	../sstuff/src
	../surfit/src
)

if (ZLIB_FOUND)
	set(INCL_DIRS ${INCL_DIRS} ${ZLIB_INCLUDE_DIR})
endif(ZLIB_FOUND)

include_directories( ${INCL_DIRS} )

add_library(${PROJ_NAME} SHARED ${srcs_cpp} ${hdrs})

target_link_libraries(${PROJ_NAME} libsstuff libsurfit)

if (ZLIB_FOUND)
	target_link_libraries(${PROJ_NAME} ${ZLIB_LIBRARIES})
endif(ZLIB_FOUND)

set_target_properties( ${PROJ_NAME} PROPERTIES PREFIX "" )

install(TARGETS ${PROJ_NAME} DESTINATION ${SURFIT_LIBDIR})

#
# the Tcl plugin, only when the Tcl front end is being built
#

if (SURFIT_BUILD_TCL)
	add_library(globe_tcl MODULE src/globe_wrap.cxx)

	target_include_directories(globe_tcl PRIVATE ${TCL_INCLUDE_PATH} ${INCL_DIRS})

	target_link_libraries(globe_tcl
		${PROJ_NAME}
		libsstuff
		libsurfit
		${TCL_LIBRARY}
	)

	set_target_properties(globe_tcl PROPERTIES
		PREFIX ""
		OUTPUT_NAME "libglobe"
		LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
	)

	install(TARGETS globe_tcl DESTINATION ${SURFIT_LIBDIR})
endif()

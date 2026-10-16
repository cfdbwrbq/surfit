# The format library and, when the Tcl front end is built, its Tcl plugin.
#
# libsurfit_io_core contains the format code and has no Tcl dependency at all.
# surfit_io_wrap.cxx is the pre-generated SWIG wrapper, which is the Tcl plugin:
# it is built as a separate module and keeps the historical file name
# libsurfit_io.so, so `load libsurfit_io[info sharedlibextension]` in the
# examples keeps working.

SET( PROJ_NAME libsurfit_io_core )

PROJECT( ${PROJ_NAME} )

FILE(GLOB_RECURSE srcs_cpp src/*.c*)
FILE(GLOB_RECURSE hdrs src/*.h*)

# The wrapper belongs to the plugin target below, not to the library.
list(REMOVE_ITEM srcs_cpp ${CMAKE_CURRENT_SOURCE_DIR}/src/surfit_io_wrap.cxx)


#
# includes
#
set (INCL_DIRS 	src
		${CMAKE_BINARY_DIR}
		../sstuff/src
		../surfit/src
)

if (JPEG_FOUND)
	set(INCL_DIRS ${INCL_DIRS} ${JPEG_INCLUDE_DIR})
endif(JPEG_FOUND)

if (NETCDF_FOUND)
	set(INCL_DIRS ${INCL_DIRS} ${NETCDF_INCLUDES})
endif(NETCDF_FOUND)


include_directories( ${INCL_DIRS} )

#
# shared libs
#

add_library(${PROJ_NAME} SHARED ${srcs_cpp} ${hdrs})

set(LINK_LIBS ${PROJ_NAME} libsstuff libsurfit)

if (JPEG_FOUND)
	set(LINK_LIBS ${LINK_LIBS} ${JPEG_LIBRARY})
endif()

if (NETCDF_FOUND)
	set(LINK_LIBS ${LINK_LIBS} ${NETCDF_LIBRARIES})
endif()

target_link_libraries(${LINK_LIBS})

set_target_properties( ${PROJ_NAME} PROPERTIES PREFIX "" )

#
# install
#

install(TARGETS ${PROJ_NAME} DESTINATION ${SURFIT_LIBDIR})

#
# the Tcl plugin, only when the Tcl front end is being built
#

if (SURFIT_BUILD_TCL)
	add_library(surfit_io_tcl MODULE src/surfit_io_wrap.cxx)

	target_include_directories(surfit_io_tcl PRIVATE ${TCL_INCLUDE_PATH})

	target_link_libraries(surfit_io_tcl
		${PROJ_NAME}
		libsstuff
		libsurfit
		${TCL_LIBRARY}
	)

	set_target_properties(surfit_io_tcl PROPERTIES
		PREFIX ""
		OUTPUT_NAME "libsurfit_io"
		LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
	)

	install(TARGETS surfit_io_tcl DESTINATION ${SURFIT_LIBDIR})
endif()

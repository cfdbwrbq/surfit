SET( PROJ_NAME surfit ) 

PROJECT( ${PROJ_NAME} )

FILE(GLOB_RECURSE srcs_cpp src/*.cpp)
FILE(GLOB_RECURSE hdrs src/*.h*)

include_directories(
${TCL_INCLUDE_PATH}
src
${CMAKE_BINARY_DIR}
../sstuff/src
)


add_executable(${PROJ_NAME} ${srcs_cpp}  ${hdrs} )

target_link_libraries(${PROJ_NAME}
${TCL_LIBRARY}
)

# The build tree keeps the development copy of the Python package at
# bin/surfit, which is where an executable of that name would go.  The binary is
# therefore built as bin/surfit-cli and installed under its real name.
set_target_properties(${PROJ_NAME} PROPERTIES OUTPUT_NAME "surfit-cli")

install(TARGETS ${PROJ_NAME} RUNTIME DESTINATION bin RENAME surfit)


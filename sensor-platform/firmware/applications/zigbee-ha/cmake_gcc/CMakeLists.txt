# Define minimal required version of CMake.
cmake_minimum_required(VERSION "3.25")

# Project definition
project(
	nowacontrol-zigbee-ha
	VERSION 1.0
	LANGUAGES C CXX ASM
)

# Include the definition of the slc_nowacontrol-zigbee-ha target,
# which contains the content of the SLC project
include(nowacontrol-zigbee-ha.cmake)

add_executable(nowacontrol-zigbee-ha
    # Sensor HAL sources
    ${CMAKE_CURRENT_LIST_DIR}/../../../hal/sensor-interface/onewire.c
    ${CMAKE_CURRENT_LIST_DIR}/../../../hal/sensor-interface/ds18b20.c
    ${CMAKE_CURRENT_LIST_DIR}/../../../hal/sensor-interface/sensor_hal.c
)

target_include_directories(nowacontrol-zigbee-ha PUBLIC
    # Sensor HAL include path
    ${CMAKE_CURRENT_LIST_DIR}/../../../hal/sensor-interface
)

target_compile_definitions(nowacontrol-zigbee-ha PUBLIC
    # Add additional macros here
)

target_compile_options(nowacontrol-zigbee-ha PUBLIC
    # Set additional compiler flags here
)

target_link_options(nowacontrol-zigbee-ha PUBLIC
    # Set additional linker flags here
)

# Link with the content defined in the SLC project
target_link_libraries(nowacontrol-zigbee-ha PRIVATE
    slc
)

# Include managed project content if available
include(nowacontrol-zigbee-ha_project.cmake OPTIONAL RESULT_VARIABLE managed_project)
if(managed_project)
    message(STATUS "Using managed project content from ${managed_project}")
endif()

# Force the gcc linker command
set_target_properties(nowacontrol-zigbee-ha PROPERTIES LINKER_LANGUAGE C)

# Create .bin, .hex and .s37 artifacts after building the project
add_custom_command(TARGET nowacontrol-zigbee-ha
    POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} ${OBJCOPY_SREC_CMD} "$<TARGET_FILE:nowacontrol-zigbee-ha>" "$<TARGET_FILE_DIR:nowacontrol-zigbee-ha>/$<TARGET_FILE_BASE_NAME:nowacontrol-zigbee-ha>.s37"
    COMMAND ${CMAKE_OBJCOPY} ${OBJCOPY_IHEX_CMD} "$<TARGET_FILE:nowacontrol-zigbee-ha>" "$<TARGET_FILE_DIR:nowacontrol-zigbee-ha>/$<TARGET_FILE_BASE_NAME:nowacontrol-zigbee-ha>.hex"
    COMMAND ${CMAKE_OBJCOPY} ${OBJCOPY_BIN_CMD}  "$<TARGET_FILE:nowacontrol-zigbee-ha>" "$<TARGET_FILE_DIR:nowacontrol-zigbee-ha>/$<TARGET_FILE_BASE_NAME:nowacontrol-zigbee-ha>.bin" 
)

# Run post-build pipeline to perform additional post-processing
if(post_build_command)
add_custom_command(TARGET nowacontrol-zigbee-ha
    POST_BUILD
    WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/..
    COMMAND ${post_build_command}
)
endif()
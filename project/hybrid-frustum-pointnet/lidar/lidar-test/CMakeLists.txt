# Collect source files
file(GLOB_RECURSE SOURCES
    "${CMAKE_SOURCE_DIR}/src/*.cpp"
    "${CMAKE_SOURCE_DIR}/src/*.h"
)

file(GLOB_RECURSE UTIL_SOURCES
    "${CMAKE_SOURCE_DIR}/src/util/*.h"
)

# Common include directories
set(COMMON_INCLUDE_DIRS
    ${CMAKE_SOURCE_DIR}/include/unitree_lidar/include
    ${CMAKE_SOURCE_DIR}/include/cpp-httplib/include
    ${PCL_INCLUDE_DIRS}
)

# Common libraries
set(COMMON_LIBRARIES
    JsonCpp::JsonCpp
    tomlplusplus::tomlplusplus
    unitree_lidar_sdk
    ${PCL_LIBRARIES}
)

# Function to create executables
function(create_executable target_name source_files)
    add_executable(${target_name} ${source_files})
    target_include_directories(${target_name} PRIVATE ${COMMON_INCLUDE_DIRS})
    target_link_libraries(${target_name} PRIVATE ${COMMON_LIBRARIES})
endfunction()

# Test executables
create_executable(test_lidar_pt_cloud
    ${CMAKE_SOURCE_DIR}/lidar-test/test-lidar-pt-cloud.cpp
)

create_executable(test_frustum
    ${CMAKE_SOURCE_DIR}/lidar-test/frustum-point-test.cpp
    ${UTIL_SOURCES}
)

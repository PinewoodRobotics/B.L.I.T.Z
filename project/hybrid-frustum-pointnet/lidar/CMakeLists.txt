cmake_minimum_required(VERSION 3.15)
project(lidar_project)

# Specify C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(jsoncpp REQUIRED)
find_package(tomlplusplus REQUIRED)
find_package(flann REQUIRED)
include_directories(${FLANN_INCLUDE_DIRS})
find_package(PCL REQUIRED COMPONENTS
    common
    io
    filters
    visualization
    segmentation
    features
    kdtree
    search
)

# Add external dependencies

# Specify source files explicitly
file(GLOB_RECURSE SOURCES
    "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/*.h"
)

file(GLOB_RECURSE UTIL_SOURCES
    "${CMAKE_CURRENT_SOURCE_DIR}/src/util/*.h"
)

add_executable(${PROJECT_NAME} ${SOURCES})

add_library(unitree_lidar_sdk STATIC IMPORTED)
set_target_properties(unitree_lidar_sdk PROPERTIES
    IMPORTED_LOCATION ${CMAKE_CURRENT_SOURCE_DIR}/include/unitree_lidar/lib/libunitree_lidar_sdk.a
)

# Include directories
target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include/unitree_lidar/include
    ${CMAKE_CURRENT_SOURCE_DIR}/include/cpp-httplib/include
    ${PCL_INCLUDE_DIRS}
)

# Link libraries
target_link_libraries(${PROJECT_NAME} PRIVATE
    JsonCpp::JsonCpp
    tomlplusplus::tomlplusplus
    unitree_lidar_sdk
    ${PCL_LIBRARIES}
)

# Apply PCL definitions
add_definitions(${PCL_DEFINITIONS})

add_subdirectory("lidar-test")
add_subdirectory("tests")
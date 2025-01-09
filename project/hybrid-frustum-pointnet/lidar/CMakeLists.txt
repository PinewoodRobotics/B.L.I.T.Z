cmake_minimum_required(VERSION 3.15)
project(lidar_project)

# Specify C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Find required packages
find_package(cpr REQUIRED)
find_package(jsoncpp REQUIRED)
find_package(tomlplusplus REQUIRED)
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
add_subdirectory(external/cpp-httplib)

# Specify source files explicitly
file(GLOB_RECURSE SOURCES
    "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/*.h"
)

# Create the executable
add_executable(${PROJECT_NAME} ${SOURCES})

# Add the Unitree lidar SDK as an imported library
add_library(unitree_lidar_sdk STATIC IMPORTED)
set_target_properties(unitree_lidar_sdk PROPERTIES
    IMPORTED_LOCATION ${CMAKE_CURRENT_SOURCE_DIR}/unitree_lidar/lib/libunitree_lidar_sdk.a
)

# Include directories
target_include_directories(${PROJECT_NAME} PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/unitree_lidar/include
    ${PCL_INCLUDE_DIRS}
)

# Link libraries
target_link_libraries(${PROJECT_NAME} PRIVATE
    cpr::cpr
    JsonCpp::JsonCpp
    tomlplusplus::tomlplusplus
    unitree_lidar_sdk
    httplib::httplib
    ${PCL_LIBRARIES}
)

# Apply PCL definitions
add_definitions(${PCL_DEFINITIONS})

# Add compiler warnings
if (CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(${PROJECT_NAME} PRIVATE -Wall -Wextra -Wpedantic)
elseif (CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    target_compile_options(${PROJECT_NAME} PRIVATE /W4 /permissive-)
endif()
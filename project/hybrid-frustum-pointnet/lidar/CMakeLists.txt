cmake_minimum_required(VERSION 3.15)
project(lidar_project)

# Specify C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(jsoncpp REQUIRED)
find_package(tomlplusplus REQUIRED)
find_package(flann REQUIRED)
find_package(websocketpp REQUIRED)
find_package(Protobuf REQUIRED)
find_package(Eigen3 REQUIRED)
include_directories(${EIGEN3_INCLUDE_DIRS})
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
include_directories(${PCL_INCLUDE_DIRS})
link_directories(${PCL_LIBRARY_DIRS})
add_definitions(${PCL_DEFINITIONS})

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
    ${CMAKE_CURRENT_SOURCE_DIR}/include/proto/project/common/proto
    ${PCL_INCLUDE_DIRS}
    ${Protobuf_INCLUDE_DIRS}
)

# Link libraries
target_link_libraries(${PROJECT_NAME} PRIVATE
    JsonCpp::JsonCpp
    tomlplusplus::tomlplusplus
    unitree_lidar_sdk
    websocketpp::websocketpp
    protobuf::libprotobuf
    ${PCL_LIBRARIES}
)

# Apply PCL definitions
add_definitions(${PCL_DEFINITIONS})

# add_subdirectory("lidar-test")
# add_subdirectory("tests")
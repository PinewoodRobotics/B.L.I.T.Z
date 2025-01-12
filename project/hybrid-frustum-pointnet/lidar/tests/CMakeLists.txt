# Find GTest
find_package(GTest REQUIRED)

# Collect test source files
file(GLOB_RECURSE TEST_SOURCES
    "${CMAKE_CURRENT_SOURCE_DIR}/*.cpp"
)

# Include directories for unitree_lidar_sdk and others
set(TEST_INCLUDE_DIRS
    ${CMAKE_SOURCE_DIR}/include/unitree_lidar/include
    ${CMAKE_SOURCE_DIR}/include/cpp-httplib/include
    ${CMAKE_CURRENT_SOURCE_DIR}
)

# Libraries to link
set(TEST_LIBRARIES
    GTest::GTest
    GTest::Main
    unitree_lidar_sdk
)

# Add the test executable
add_executable(run_tests ${TEST_SOURCES})

# Apply include directories and link libraries
target_include_directories(run_tests PRIVATE ${TEST_INCLUDE_DIRS})
target_link_libraries(run_tests PRIVATE ${TEST_LIBRARIES})

# Enable testing and register the test executable
enable_testing()
add_test(NAME RunAllTests COMMAND run_tests)

cmake_minimum_required(VERSION 3.10)

# Set the project name
project(navx2)

# Find required packages
find_package(Boost REQUIRED COMPONENTS system)
find_package(Threads REQUIRED)

# Add library
add_library(navx2
    STATIC
    src/autobahn.cpp
        src/autobahn.h
)

# Include directories
target_include_directories(navx2
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${Boost_INCLUDE_DIRS}
)

# Link libraries
target_link_libraries(navx2
    PUBLIC
    Threads::Threads
    Boost::system
)

# Set C++ standard
target_compile_features(navx2 PUBLIC cxx_std_17)

# Add compile options
target_compile_options(navx2
    PRIVATE
    -Wall
    -Wextra
    -Wpedantic
)

# make main.cpp executable
add_executable(main src/main.cpp)
target_link_libraries(main navx2)
cmake_minimum_required(VERSION 3.16)
project(sample_cpp_executable LANGUAGES CXX)
add_executable(sample_cpp_executable main.cpp)
target_link_libraries(sample_cpp_executable PRIVATE ${CMAKE_DL_LIBS})

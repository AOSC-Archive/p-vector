cmake_minimum_required(VERSION 3.2)
project(p_vector)

set(CMAKE_CXX_STANDARD 17)

set(LIBEXEC_PATH "libexec/p-vector")

add_subdirectory(native)
add_subdirectory(python)

install(PROGRAMS p-vector DESTINATION bin)

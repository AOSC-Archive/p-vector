cmake_minimum_required(VERSION 3.2)
project(p_vector)

set(CMAKE_CXX_STANDARD 11)

set(LIBEXEC_PATH "libexec/p-vector")
set(MAN_PATH "share/man")

add_subdirectory(native)
add_subdirectory(python)
add_subdirectory(doc)

install(PROGRAMS p-vector DESTINATION bin)

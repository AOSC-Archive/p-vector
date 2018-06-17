cmake_minimum_required(VERSION 3.11)
project(p_vector)

set(CMAKE_CXX_STANDARD 17)

add_executable(p_vector main.cpp utils.h entry.h package.cpp package.h elf_dependency.cpp elf_dependency.h)
target_link_libraries(p_vector archive pthread crypto)

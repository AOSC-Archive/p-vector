cmake_minimum_required(VERSION 3.2)
project(p_vector)

set(CMAKE_CXX_STANDARD 17)

find_package(LibArchive REQUIRED)
find_package(OpenSSL REQUIRED)

add_executable(p_vector
        main.cpp
        utils.h
        entry.h
        package.cpp
        package.h
        elf_dependency.cpp
        elf_dependency.h)

target_include_directories(p_vector PRIVATE
        ${LibArchive_INCLUDE_DIRS}
        ${OPENSSL_INCLUDE_DIR})

target_link_libraries(p_vector
        ${LibArchive_LIBRARIES}
        ${OPENSSL_CRYPTO_LIBRARY})

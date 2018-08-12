find_package(LibArchive REQUIRED)
find_package(OpenSSL REQUIRED)

add_definitions(-D_FILE_OFFSET_BITS=64)
add_compile_options(-Wall -Wextra -Werror)
add_compile_options(-O3 -g1)

add_library(pkgscan STATIC
        package.cpp
        elf_dependency.cpp
        package_archive_custom.cpp)

target_include_directories(pkgscan PRIVATE
        ../include
        ${LibArchive_INCLUDE_DIRS}
        ${OPENSSL_INCLUDE_DIR})

target_link_libraries(pkgscan
        ${LibArchive_LIBRARIES}
        ${OPENSSL_CRYPTO_LIBRARY})

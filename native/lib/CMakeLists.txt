find_package(LibArchive REQUIRED)
find_package(OpenSSL REQUIRED)

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

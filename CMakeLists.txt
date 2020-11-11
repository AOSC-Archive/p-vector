cmake_minimum_required(VERSION 3.2)
project(p-vector)

set(CMAKE_CXX_STANDARD 11)

set(LIBEXEC_PATH "libexec/p-vector")
set(MAN_PATH "share/man")

add_subdirectory(native)
add_subdirectory(python)
add_subdirectory(doc)

install(PROGRAMS p-vector DESTINATION bin)

# CPack settings
set(CPACK_PACKAGE_VENDOR "AOSC")
set(CPACK_PACKAGE_VERSION $ENV{PV_VERSION})
set(CPACK_PACKAGE_DESCRIPTION "Scanner for .deb Packages and ELF Dependencies")
set(CPACK_DEBIAN_PACKAGE_MAINTAINER "AOSC Infra Team <infra@lists.aosc.io>")
set(CPACK_DEBIAN_PACKAGE_DEPENDS "libarchive13, libssl1.1, python3")
set(CPACK_GENERATOR DEB TXZ)
set(CPACK_PACKAGE_CHECKSUM SHA256)
include(CPack)

configure_file(main.h.in main.h @ONLY)

set_source_files_properties(
        ${PROTO_HEADERS}
        ${PROTO_SOURCES}
        PROPERTIES GENERATED TRUE)

add_executable(pkgscan_cli
        main.cpp
        main.h
        ${PROTO_HEADERS}
        ${PROTO_SOURCES})

target_include_directories(pkgscan_cli PRIVATE
        include
        ${CMAKE_CURRENT_BINARY_DIR})

add_subdirectory(lib)

target_link_libraries(pkgscan_cli
        pkgscan
        ${Protobuf_LIBRARIES})

install(TARGETS pkgscan_cli
        RUNTIME DESTINATION ${LIBEXEC_PATH})

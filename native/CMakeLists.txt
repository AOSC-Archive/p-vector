add_definitions(-D_FILE_OFFSET_BITS=64)
add_compile_options(-Wall -Wextra -Werror)
add_compile_options(-O3 -g1)

add_executable(pkgscan_cli
        main.cpp)

target_include_directories(pkgscan_cli PRIVATE
        include
        ${CMAKE_CURRENT_BINARY_DIR})

add_subdirectory(lib)

target_link_libraries(pkgscan_cli
        pkgscan)

install(TARGETS pkgscan_cli
        RUNTIME DESTINATION ${LIBEXEC_PATH})

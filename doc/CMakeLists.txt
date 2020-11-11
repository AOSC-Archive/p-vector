find_program(PANDOC pandoc)
if (PANDOC)
        message(STATUS "Will build documentation")
        add_custom_command(
                OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/p-vector.1"
                COMMAND pandoc -s -t man -o "${CMAKE_CURRENT_BINARY_DIR}/p-vector.1")
        add_custom_command(
                OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/p-vector.1.xz"
                DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/p-vector.1"
                COMMAND xz -9f "${CMAKE_CURRENT_BINARY_DIR}/p-vector.1"
                )
        add_custom_target(manual ALL
                DEPENDS "${CMAKE_CURRENT_BINARY_DIR}/p-vector.1.xz"
                )
        install(FILES ${CMAKE_CURRENT_BINARY_DIR}/p-vector.1.xz
                DESTINATION ${MAN_PATH}/man1
                )
else()
        message(WARNING "Pandoc not found. Documentation generation disabled.")
endif()

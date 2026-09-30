cmake_minimum_required(VERSION 3.19)
project(rocketperf LANGUAGES C)
set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_library(rocketperf_core STATIC
    src/core/status.c src/core/root.c src/nozzle/ideal.c)
target_include_directories(rocketperf_core PUBLIC include)
if(NOT MSVC)
    target_link_libraries(rocketperf_core PUBLIC m)
endif()

add_executable(rocketperf
    src/cli/main.c src/adapters/case_file.c
    src/adapters/json_report.c src/adapters/platform.c)
target_include_directories(rocketperf PRIVATE src/adapters)
target_link_libraries(rocketperf PRIVATE rocketperf_core)
if(MINGW)
    target_link_options(rocketperf PRIVATE -municode)
endif()

include(CTest)
if(BUILD_TESTING)
    add_executable(test_core tests/test_core.c)
    target_link_libraries(test_core PRIVATE rocketperf_core)
    add_test(NAME core COMMAND test_core)
    find_package(Python3 COMPONENTS Interpreter QUIET)
    if(Python3_Interpreter_FOUND)
        add_test(NAME cli COMMAND "${Python3_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_cli.py"
            --binary "$<TARGET_FILE:rocketperf>")
    endif()
endif()

foreach(target rocketperf_core rocketperf test_core)
    if(TARGET ${target})
        if(MSVC)
            target_compile_options(${target} PRIVATE /W4 /WX /fp:precise)
            target_compile_definitions(${target} PRIVATE _CRT_SECURE_NO_WARNINGS)
        else()
            target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic -Werror
                -Wconversion -Wshadow -Wstrict-prototypes -Wmissing-prototypes -fno-common)
        endif()
    endif()
endforeach()

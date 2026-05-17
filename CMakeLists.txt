cmake_minimum_required(VERSION 3.18)
project(moira_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Python3 COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_moira_native
    src/native/bindings/moira_native.cpp
    src/native/src/lola.cpp
)

target_include_directories(_moira_native PRIVATE src/native/include)

set_target_properties(_moira_native PROPERTIES
    OUTPUT_NAME "_moira_native"
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)

if(MOIRA_EXTENSION_FULL_OUTPUT_PATH)
    get_filename_component(MOIRA_EXTENSION_OUTPUT_DIR "${MOIRA_EXTENSION_FULL_OUTPUT_PATH}" DIRECTORY)

    set_target_properties(_moira_native PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY "${MOIRA_EXTENSION_OUTPUT_DIR}"
        RUNTIME_OUTPUT_DIRECTORY "${MOIRA_EXTENSION_OUTPUT_DIR}"
        ARCHIVE_OUTPUT_DIRECTORY "${MOIRA_EXTENSION_OUTPUT_DIR}"
        LIBRARY_OUTPUT_DIRECTORY_RELEASE "${MOIRA_EXTENSION_OUTPUT_DIR}"
        RUNTIME_OUTPUT_DIRECTORY_RELEASE "${MOIRA_EXTENSION_OUTPUT_DIR}"
        ARCHIVE_OUTPUT_DIRECTORY_RELEASE "${MOIRA_EXTENSION_OUTPUT_DIR}"
        LIBRARY_OUTPUT_DIRECTORY_DEBUG "${MOIRA_EXTENSION_OUTPUT_DIR}"
        RUNTIME_OUTPUT_DIRECTORY_DEBUG "${MOIRA_EXTENSION_OUTPUT_DIR}"
        ARCHIVE_OUTPUT_DIRECTORY_DEBUG "${MOIRA_EXTENSION_OUTPUT_DIR}"
    )
endif()

find_package(OpenMP QUIET)
if(OpenMP_CXX_FOUND)
    target_link_libraries(_moira_native PRIVATE OpenMP::OpenMP_CXX)
endif()

install(TARGETS _moira_native LIBRARY DESTINATION moira RUNTIME DESTINATION moira)

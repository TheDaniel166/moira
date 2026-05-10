cmake_minimum_required(VERSION 3.12)
project(moira_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Explicitly include Python and pybind11 directories to bypass config failures
include_directories("C:/Python314/Include")
include_directories("C:/Users/nilad/AppData/Roaming/Python/Python314/site-packages/pybind11/include")
include_directories(src/native/include)

# Define the extension module manually under a private backend name.
add_library(_moira_native MODULE 
    src/native/bindings/moira_native.cpp
    src/native/src/lola.cpp
)

# Link against Python library
target_link_libraries(_moira_native PRIVATE "C:/Python314/libs/python314.lib")

# Set target properties to match Python's extension requirements
set_target_properties(_moira_native PROPERTIES
    PREFIX ""
    SUFFIX ".pyd"
    OUTPUT_NAME "_moira_native"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/moira"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/moira"
    LIBRARY_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/moira"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/moira"
    LIBRARY_OUTPUT_DIRECTORY_DEBUG "${CMAKE_SOURCE_DIR}/moira"
    RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_SOURCE_DIR}/moira"
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)

# Installation (optional for now, we'll build in place)
install(TARGETS _moira_native DESTINATION moira)

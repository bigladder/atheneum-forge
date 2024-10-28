# Copyright (c) {% if start_year is defined and start_year != year %}{{ start_year }} - {% endif %}{{ year }} Big Ladder Software LLC. All rights reserved.
# See the LICENSE.txt file for additional terms and conditions.
# NOTE: THIS FILE IS AUTO-GENERATED. DO NOT EDIT.
# Main library
set(library_sources
    {%- for src in files_src %}
    ${PROJECT_SOURCE_DIR}/src/{{ src.name }}
    {%- endfor %}
    {%- for h in headers_public %}
    ${PROJECT_SOURCE_DIR}/include/{{ h.code_path }}
    {%- endfor %}
    {%- for h in headers_private %}
    ${PROJECT_SOURCE_DIR}/src/{{ h.name }}
    {%- endfor %}
    ${PROJECT_BINARY_DIR}/include/${PROJECT_NAME}/version.h
)

if (${PROJECT_NAME}_STATIC_LIB)
    add_library(${PROJECT_NAME}lib STATIC ${library_sources})
    set_target_properties(${PROJECT_NAME}lib PROPERTIES COMPILE_FLAGS "-D${PROJECT_NAME}_STATIC_DEFINE")
else ()
    set(CMAKE_MACOSX_RPATH 1)
    add_library(${PROJECT_NAME}lib SHARED ${library_sources})
endif ()

target_include_directories(${PROJECT_NAME}lib
    PUBLIC "${PROJECT_SOURCE_DIR}/include"
    PUBLIC "${PROJECT_BINARY_DIR}/include"
    PRIVATE "${PROJECT_SOURCE_DIR}/src"
)

target_compile_features(${PROJECT_NAME}lib PRIVATE cxx_std_{{ cpp_std }})

target_link_libraries(${PROJECT_NAME}lib PRIVATE fmt)

target_link_libraries(${PROJECT_NAME}lib PRIVATE ${PROJECT_NAME}_build_options)
target_compile_features(${PROJECT_NAME}lib PRIVATE cxx_std_{{ cpp_std }})

include(GenerateExportHeader)
generate_export_header(${PROJECT_NAME}lib)

# If MSVC_RUNTIME_LIBRARY is not by a parent project use the default.
# It's not clear why this is needed, since documentation indicates it
#   should be happening with the CMP0091 policy set to NEW.
get_target_property(RTL ${PROJECT_NAME}lib MSVC_RUNTIME_LIBRARY)
if ("${RTL}" STREQUAL "RTL-NOTFOUND")
    set_target_properties(${PROJECT_NAME}lib PROPERTIES MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
endif ()

if (${PROJECT_NAME}_COVERAGE)
    add_coverage(${PROJECT_NAME}lib)
endif ()

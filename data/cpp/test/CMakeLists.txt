# Copyright (c) {% if start_year is defined and start_year != year %}{{ start_year }} - {% endif %}{{ year }} Big Ladder Software, LLC.
# See the LICENSE.txt file for additional terms and conditions.
# NOTE: THIS FILE IS AUTO-GENERATED. DO NOT EDIT.
set(test_sources
{%- for tf in files_test %}
  {{ tf.name }}
{%- endfor %}
)

add_executable(${PROJECT_NAME}_tests ${test_sources})

target_link_libraries(${PROJECT_NAME}_tests
  PRIVATE ${PROJECT_NAME} gtest ${PROJECT_NAME}_build_options
  GTest::gtest_main 
{%- for dep in deps %}
{%- if dep.add_to_cmake %}
{%- if dep.link_library_spec is defined %}
  {{ dep.link_library_spec }}
{%- else %}
  {{ dep.name }}
{%- endif %}
{%- endif %}
{%- endfor %}
)
target_compile_features(${PROJECT_NAME}_tests PRIVATE cxx_std_{{ cpp_std }})

include(GoogleTest)
gtest_discover_tests(${PROJECT_NAME}_tests)

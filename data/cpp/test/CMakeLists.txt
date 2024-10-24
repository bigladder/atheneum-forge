set(test_sources
{%- for tf in files_test %}
  {{ tf.name }}
{%- endfor %}
)

add_executable(${PROJECT_NAME}_tests ${test_sources})

target_link_libraries(${PROJECT_NAME}_tests PRIVATE ${PROJECT_NAME} gtest ${PROJECT_NAME}_build_options)
target_compile_features(${PROJECT_NAME}_tests PRIVATE cxx_std_{{ cpp_std }})

include(GoogleTest)
gtest_discover_tests(${PROJECT_NAME}_tests)

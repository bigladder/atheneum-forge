# Copyright (c) {% if start_year is defined and start_year != year %}{{ start_year }} - {% endif %}{{ year }} Big Ladder Software LLC. All rights reserved.
# See the LICENSE.txt file for additional terms and conditions.
# NOTE: THIS FILE IS AUTO-GENERATED. DO NOT EDIT.
{% if files_app_config|length > 0 -%}
configure_file(
{%- for config in files_app_config %}
	${PROJECT_SOURCE_DIR}/app/{{ config.name }}
	${PROJECT_BINARY_DIR}/app/{{ config.name|replace(".in", "") }}
{%- endfor %}
)
{%- endif %}
{%- for f in files_app %}

add_executable(APP_{{ f.name|replace(".cpp", "") }}
  {{ f.name }}
)
set_target_properties(APP_{{ f.name|replace(".cpp", "") }}
  PROPERTIES OUTPUT_NAME {{ f.name|replace(".cpp", "") }}
)
target_include_directories(APP_{{ f.name|replace(".cpp", "") }}
	PUBLIC ${PROJECT_SOURCE_DIR}/include
	PRIVATE ${PROJECT_BINARY_DIR}/app
)
target_link_libraries(APP_{{ f.name|replace(".cpp", "") }}
  ${PROJECT_NAME}
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
{%- endfor %}

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

add_executable({{ f.name|replace(".cpp", "") }}
  {{ f.name }}
)
target_include_directories({{ f.name|replace(".cpp", "") }}
	PUBLIC ${PROJECT_SOURCE_DIR}/include
	PRIVATE ${PROJECT_BINARY_DIR}/app
)
target_link_libraries({{ f.name|replace(".cpp", "") }}
  ${PROJECT_NAME}lib
{%- for dep in deps %}
{%- if dep.add_to_cmake %}
  {{ dep.name }}
{%- endif %}
{%- endfor %}
)
{%- endfor %}

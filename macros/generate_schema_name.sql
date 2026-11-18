{# Keep everything in the target schema: DuckDB is a single-file warehouse
   and separate schemas per model group add nothing here. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ target.schema }}
{%- endmacro %}

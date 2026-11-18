{# Severity of one incident, as a single comparable number.
   Hospitalization counts 1 point per person, amputation 2, eye loss 3.
   Used by int_sir_clean and fact_incidents. #}
{% macro severity_score(hospitalized, amputation, eye_loss) %}
    (coalesce({{ hospitalized }}, 0)
     + 2 * coalesce({{ amputation }}, 0)
     + 3 * coalesce({{ eye_loss }}, 0))
{% endmacro %}

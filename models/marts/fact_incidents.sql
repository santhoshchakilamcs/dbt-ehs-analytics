{{ config(materialized='table') }}

-- Grain: one row per OSHA severe injury report.
select
    md5(report_id) as incident_key,
    report_id,
    employer_key,
    cast(strftime(event_date, '%Y%m%d') as integer) as date_key,
    event_date,
    md5(event_code) as event_key,
    md5(nature_code) as nature_key,
    md5(source_code) as source_key,
    md5(body_part_code) as body_part_key,
    state,
    naics_code,
    naics_sector,
    is_federal,
    people_hospitalized,
    people_amputated,
    people_eye_loss,
    is_hospitalized,
    is_amputation,
    is_eye_loss,
    has_inspection,
    inspection_nr,
    severity_score
from {{ ref('int_sir_clean') }}

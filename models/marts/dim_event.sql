{{ config(materialized='table') }}

-- One row per event code. The same code occasionally carries slightly
-- different titles in the source, so keep one title per code (max).
select
    md5(event_code) as event_key,
    event_code,
    max(event_title) as event_title
from {{ ref('int_sir_clean') }}
group by 1, 2

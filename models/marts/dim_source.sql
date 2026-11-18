{{ config(materialized='table') }}

select
    md5(source_code) as source_key,
    source_code,
    max(source_title) as source_title
from {{ ref('int_sir_clean') }}
group by 1, 2

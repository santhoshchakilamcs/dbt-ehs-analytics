{{ config(materialized='table') }}

select
    md5(body_part_code) as body_part_key,
    body_part_code,
    max(body_part_title) as body_part_title
from {{ ref('int_sir_clean') }}
group by 1, 2

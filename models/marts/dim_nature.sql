{{ config(materialized='table') }}

select
    md5(nature_code) as nature_key,
    nature_code,
    max(nature_title) as nature_title
from {{ ref('int_sir_clean') }}
group by 1, 2

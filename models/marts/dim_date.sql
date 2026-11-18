{{ config(materialized='table') }}

with spine as (
    select cast(d as date) as date_day
    from range(date '2015-01-01', date '2026-01-01', interval 1 day) as t(d)
)

select
    cast(strftime(date_day, '%Y%m%d') as integer) as date_key,
    date_day,
    year(date_day) as year,
    quarter(date_day) as quarter,
    month(date_day) as month,
    monthname(date_day) as month_name,
    day(date_day) as day_of_month,
    dayofweek(date_day) as day_of_week,
    case when dayofweek(date_day) in (0, 6) then true else false end as is_weekend
from spine

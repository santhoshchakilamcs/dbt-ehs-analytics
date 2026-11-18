{{ config(materialized='table') }}

-- MetricFlow time spine: one row per day, 2015-01-01 to 2025-12-31.
select cast(d as date) as date_day
from range(date '2015-01-01', date '2026-01-01', interval 1 day) as t(d)

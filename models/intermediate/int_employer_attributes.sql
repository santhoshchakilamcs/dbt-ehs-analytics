{{ config(materialized='view') }}

-- One row per employer, carrying the attributes of its latest incident.
-- This is the snapshot source: when an employer's NAICS or address changes
-- across incidents, the check-strategy snapshot records a new SCD Type 2 version.
with ranked as (
    select
        *,
        row_number() over (
            partition by employer_key
            order by event_date desc, report_id desc
        ) as _rn
    from {{ ref('int_sir_clean') }}
),

agg as (
    select
        employer_key,
        count(*) as incident_count,
        min(event_date) as first_event_date,
        max(event_date) as latest_event_date
    from {{ ref('int_sir_clean') }}
    group by 1
)

select
    r.employer_key,
    r.employer_name,
    r.address1,
    r.address2,
    r.city,
    r.state,
    r.zip_code,
    r.naics_code,
    r.naics_sector,
    a.incident_count,
    a.first_event_date,
    a.latest_event_date
from ranked as r
join agg as a on r.employer_key = a.employer_key
where r._rn = 1

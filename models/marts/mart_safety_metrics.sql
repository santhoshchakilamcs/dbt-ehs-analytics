{{ config(materialized='table') }}

-- Monthly safety KPIs by state and NAICS sector. Metric definitions:
--   incident_count: severe injury reports in the month.
--   hospitalization_rate: share of incidents with >= 1 person hospitalized.
--   amputation_rate: share of incidents with >= 1 amputation.
--   eye_loss_rate: share of incidents with >= 1 eye loss.
--   inspection_rate: share of incidents followed by an OSHA inspection.
--   repeat_employer_incidents: incidents at employers that reported more
--     than one incident in the same month (a repeat-occurrence signal).
--   avg_severity_score: mean severity score (hospitalized + 2*amputated
--     + 3*eye loss per incident) for the month.
with monthly as (
    select
        date_trunc('month', event_date) as month,
        state,
        naics_sector,
        count(*) as incident_count,
        sum(people_hospitalized) as people_hospitalized,
        sum(people_amputated) as people_amputated,
        sum(people_eye_loss) as people_eye_loss,
        sum(is_hospitalized) as incidents_with_hospitalization,
        sum(is_amputation) as incidents_with_amputation,
        sum(is_eye_loss) as incidents_with_eye_loss,
        sum(has_inspection) as inspections,
        count(distinct employer_key) as employers_affected,
        avg(severity_score) as avg_severity_score
    from {{ ref('fact_incidents') }}
    group by 1, 2, 3
),

repeat_employers as (
    select
        date_trunc('month', event_date) as month,
        state,
        naics_sector,
        sum(case when cnt > 1 then cnt else 0 end) as repeat_employer_incidents
    from (
        select
            event_date,
            state,
            naics_sector,
            employer_key,
            count(*) as cnt
        from {{ ref('fact_incidents') }}
        group by 1, 2, 3, 4
    )
    group by 1, 2, 3
)

select
    m.month,
    m.state,
    m.naics_sector,
    m.incident_count,
    m.people_hospitalized,
    m.people_amputated,
    m.people_eye_loss,
    m.incidents_with_hospitalization,
    m.incidents_with_hospitalization * 1.0 / nullif(m.incident_count, 0) as hospitalization_rate,
    m.incidents_with_amputation,
    m.incidents_with_amputation * 1.0 / nullif(m.incident_count, 0) as amputation_rate,
    m.incidents_with_eye_loss,
    m.incidents_with_eye_loss * 1.0 / nullif(m.incident_count, 0) as eye_loss_rate,
    m.inspections,
    m.inspections * 1.0 / nullif(m.incident_count, 0) as inspection_rate,
    m.employers_affected,
    coalesce(r.repeat_employer_incidents, 0) as repeat_employer_incidents,
    m.avg_severity_score
from monthly as m
left join repeat_employers as r
    on m.month = r.month
    and m.state = r.state
    and m.naics_sector = r.naics_sector

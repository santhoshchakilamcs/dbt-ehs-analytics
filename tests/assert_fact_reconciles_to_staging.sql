-- The fact must reconcile exactly to staging: same row count, same people totals.
select 'row_count_mismatch' as failure
where (select count(*) from {{ ref('fact_incidents') }})
   != (select count(*) from {{ ref('stg_osha_sir') }})
union all
select 'hospitalized_total_mismatch' as failure
where (select sum(people_hospitalized) from {{ ref('fact_incidents') }})
   != (select sum(coalesce(people_hospitalized, 0)) from {{ ref('stg_osha_sir') }})
union all
select 'amputation_total_mismatch' as failure
where (select sum(people_amputated) from {{ ref('fact_incidents') }})
   != (select sum(coalesce(people_amputated, 0)) from {{ ref('stg_osha_sir') }})

-- SCD Type 2 invariant: exactly one current row per employer in the snapshot.
select 'current_row_count_mismatch' as failure
where (select count(*) from {{ ref('snap_employer') }} where dbt_valid_to is null)
   != (select count(distinct employer_key) from {{ ref('snap_employer') }})

{{ config(materialized='table') }}

-- SCD Type 2 employer dimension, built from the snapshot. One row per
-- employer version; is_current marks the latest version.
select
    employer_key,
    employer_name,
    address1,
    address2,
    city,
    state,
    zip_code,
    naics_code,
    naics_sector,
    incident_count,
    first_event_date,
    latest_event_date,
    dbt_valid_from as valid_from,
    dbt_valid_to as valid_to,
    dbt_valid_to is null as is_current
from {{ ref('snap_employer') }}

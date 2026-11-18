{{ config(materialized='view') }}

with source as (
    select * from {{ source('osha', 'sir') }}
),

renamed as (
    select
        cast("ID" as varchar) as report_id,
        "UPA" as upa,
        cast("EventDate" as date) as event_date,
        trim("Employer") as employer_name,
        trim("Address1") as address1,
        trim("Address2") as address2,
        trim("City") as city,
        upper(trim("State")) as state,
        trim("Zip") as zip_code,
        cast(nullif(trim(cast("Latitude" as varchar)), '') as double) as latitude,
        cast(nullif(trim(cast("Longitude" as varchar)), '') as double) as longitude,
        trim(cast("Primary NAICS" as varchar)) as naics_code,
        cast(cast(nullif(trim(cast("Hospitalized" as varchar)), '') as double) as integer) as people_hospitalized,
        cast(cast(nullif(trim(cast("Amputation" as varchar)), '') as double) as integer) as people_amputated,
        cast(cast(nullif(trim(cast("Loss of Eye" as varchar)), '') as double) as integer) as people_eye_loss,
        nullif(trim(cast("Inspection" as varchar)), '') as inspection_nr,
        "Final Narrative" as narrative,
        trim(cast("Nature" as varchar)) as nature_code,
        trim("NatureTitle") as nature_title,
        trim(cast("Part of Body" as varchar)) as body_part_code,
        trim("Part of Body Title") as body_part_title,
        trim(cast("Event" as varchar)) as event_code,
        trim("EventTitle") as event_title,
        trim(cast("Source" as varchar)) as source_code,
        trim("SourceTitle") as source_title,
        trim(cast("Secondary Source" as varchar)) as secondary_source_code,
        trim("Secondary Source Title") as secondary_source_title,
        cast("FederalState" as integer) = 1 as is_federal
    from source
),

-- 5 report IDs appear twice in the full file; keep the earliest record per ID.
deduped as (
    select
        *,
        row_number() over (partition by report_id order by event_date, employer_name) as _rn
    from renamed
)

select * exclude (_rn)
from deduped
where _rn = 1

-- Counts of people affected can never be negative.
select report_id, people_hospitalized, people_amputated, people_eye_loss
from {{ ref('stg_osha_sir') }}
where coalesce(people_hospitalized, 0) < 0
   or coalesce(people_amputated, 0) < 0
   or coalesce(people_eye_loss, 0) < 0

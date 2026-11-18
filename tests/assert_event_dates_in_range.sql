-- Event dates must fall inside the dataset window, 2015-01-01 to 2025-11-30.
select report_id, event_date
from {{ ref('stg_osha_sir') }}
where event_date < date '2015-01-01' or event_date > date '2025-11-30'

-- Staging must deduplicate report IDs (5 duplicate IDs exist in the full file).
select report_id, count(*) as n
from {{ ref('stg_osha_sir') }}
group by 1
having count(*) > 1

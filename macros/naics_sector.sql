{# NAICS 2-digit sector name for a 6-digit NAICS code expression. #}
{% macro naics_sector(naics_code) %}
    case
        when substr({{ naics_code }}, 1, 2) = '11' then 'Agriculture, Forestry, Fishing and Hunting'
        when substr({{ naics_code }}, 1, 2) = '21' then 'Mining, Quarrying, and Oil and Gas Extraction'
        when substr({{ naics_code }}, 1, 2) = '22' then 'Utilities'
        when substr({{ naics_code }}, 1, 2) = '23' then 'Construction'
        when substr({{ naics_code }}, 1, 2) in ('31', '32', '33') then 'Manufacturing'
        when substr({{ naics_code }}, 1, 2) = '42' then 'Wholesale Trade'
        when substr({{ naics_code }}, 1, 2) in ('44', '45') then 'Retail Trade'
        when substr({{ naics_code }}, 1, 2) in ('48', '49') then 'Transportation and Warehousing'
        when substr({{ naics_code }}, 1, 2) = '51' then 'Information'
        when substr({{ naics_code }}, 1, 2) = '52' then 'Finance and Insurance'
        when substr({{ naics_code }}, 1, 2) = '53' then 'Real Estate and Rental and Leasing'
        when substr({{ naics_code }}, 1, 2) = '54' then 'Professional, Scientific, and Technical Services'
        when substr({{ naics_code }}, 1, 2) = '55' then 'Management of Companies and Enterprises'
        when substr({{ naics_code }}, 1, 2) = '56' then 'Administrative and Support and Waste Management'
        when substr({{ naics_code }}, 1, 2) = '61' then 'Educational Services'
        when substr({{ naics_code }}, 1, 2) = '62' then 'Health Care and Social Assistance'
        when substr({{ naics_code }}, 1, 2) = '71' then 'Arts, Entertainment, and Recreation'
        when substr({{ naics_code }}, 1, 2) = '72' then 'Accommodation and Food Services'
        when substr({{ naics_code }}, 1, 2) = '81' then 'Other Services (except Public Administration)'
        when substr({{ naics_code }}, 1, 2) = '92' then 'Public Administration'
        when {{ naics_code }} is null or trim({{ naics_code }}) = '' then 'Unknown / not reported'
        else 'Other / Unknown'
    end
{% endmacro %}

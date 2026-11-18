{% snapshot snap_employer %}

{{
    config(
      unique_key='employer_key',
      strategy='check',
      check_cols=['naics_code', 'address1', 'city', 'state', 'zip_code'],
    )
}}

select * from {{ ref('int_employer_attributes') }}

{% endsnapshot %}

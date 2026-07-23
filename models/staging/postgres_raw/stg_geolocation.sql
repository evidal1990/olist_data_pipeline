{{ config(
    materialized = 'incremental', 
    unique_key = ('geolocation_lat', 'geolocation_lng'),
    on_schema_change = 'fail'
) }}

select
    geolocation_zip_code_prefix,
    geolocation_lat,
    geolocation_lng,
    geolocation_city,
    geolocation_state,
    cast(updated_at as timestamp) as updated_at
from {{ source('postgres_raw', 'olist_geolocation') }}

{% if is_incremental() %}
where updated_at >= (select max(updated_at) from {{ this }})
{% endif %}
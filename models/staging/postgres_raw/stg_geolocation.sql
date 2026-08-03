{{ config(
    materialized = 'incremental', 
    unique_key = ('geolocation_zip_code_prefix', 'geolocation_lat', 'geolocation_lng', 'geolocation_city', 'geolocation_state'),
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
where cast(updated_at as timestamp) >= (select max(updated_at) from {{ this }})
{% endif %}

qualify row_number() over (
    partition by geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state
    order by updated_at desc
) = 1
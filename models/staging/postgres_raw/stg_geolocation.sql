{{ config(
    materialized = 'table'
) }}

select
    geolocation_zip_code_prefix,
    geolocation_lat,
    geolocation_lng,
    geolocation_city,
    geolocation_state,
    updated_at
from {{ source('postgres_raw', 'olist_geolocation') }}
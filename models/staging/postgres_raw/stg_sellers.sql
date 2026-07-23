{{ config(
    materialized = 'table'
) }}

select
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state,
    updated_at
from {{ source('postgres_raw', 'olist_sellers') }}
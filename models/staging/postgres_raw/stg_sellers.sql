{{ config(
    materialized = 'incremental', 
    unique_key = 'seller_id',
    on_schema_change = 'fail'
) }}

select
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state,
    cast(updated_at as timestamp) as updated_at
from {{ source('postgres_raw', 'olist_sellers') }}

{% if is_incremental() %}
where cast(updated_at as timestamp) >= (select cast(max(updated_at) as timestamp) from {{ this }})
{% endif %}
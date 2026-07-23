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
    updated_at
from {{ source('postgres_raw', 'olist_sellers') }}

{% if is_incremental() %}
where updated_at >= (select max(updated_at) from {{ this }})
{% endif %}
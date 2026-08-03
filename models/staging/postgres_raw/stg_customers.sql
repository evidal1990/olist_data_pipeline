{{ config(
    materialized = 'incremental', 
    unique_key = 'customer_id',
    on_schema_change = 'fail'
) }}

select
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state,
    cast(is_active as boolean) as is_active,
    cast(updated_at as timestamp) as updated_at
from {{ source('postgres_raw', 'olist_customers') }}

{% if is_incremental() %}
where cast(updated_at as timestamp) >= (select cast(max(updated_at) as timestamp) from {{ this }})
{% endif %}
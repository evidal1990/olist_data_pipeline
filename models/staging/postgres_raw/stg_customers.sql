{{ config(
    materialized = 'table'
) }}

select
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state,
    cast(is_active as boolean) as is_active,
    updated_at
from {{ source('postgres_raw', 'olist_customers') }}
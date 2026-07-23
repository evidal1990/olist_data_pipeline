{{ config(
    materialized = 'view'
) }}

select
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state,
    cast(is_active as boolean) as is_active
from {{ source('postgres_raw', 'olist_customers') }}
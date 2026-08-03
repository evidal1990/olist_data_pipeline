{{ config(
    materialized = 'incremental', 
    unique_key = 'order_id',
    on_schema_change = 'fail'
) }}

select
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value,
    cast(updated_at as timestamp) as updated_at
from {{ source('postgres_raw', 'olist_order_payments') }}

{% if is_incremental() %}
where cast(updated_at as timestamp) >= (select max(updated_at) from {{ this }})
{% endif %}
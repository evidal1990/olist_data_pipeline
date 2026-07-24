{{ config(
    materialized = 'incremental', 
    unique_key = 'order_id',
    on_schema_change = 'fail'
) }}

select
    order_id,
    customer_id,
    order_status,
    order_approved_at,
    order_purchase_timestamp,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    order_estimated_delivery_date,
    cast(updated_at as timestamp) as updated_at
from {{ source('postgres_raw', 'olist_orders') }}

{% if is_incremental() %}
where updated_at >= (select max(updated_at) from {{ this }})
{% endif %}
{{ config(
    materialized = 'incremental', 
    unique_key = ('order_id', 'order_item_id'),
    on_schema_change = 'fail'
) }}

select
    order_id,
    order_item_id,
    product_id,
    seller_id,
    price,
    freight_value,
    shipping_limit_date,
    cast(updated_at as timestamp) as updated_at
from {{ source('postgres_raw', 'olist_order_items') }}

{% if is_incremental() %}
where updated_at >= (select max(updated_at) from {{ this }})
{% endif %}
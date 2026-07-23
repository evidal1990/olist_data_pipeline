{{ config(
    materialized = 'table'
) }}

select
    order_id,
    order_item_id,
    product_id,
    seller_id,
    price,
    freight_value,
    shipping_limit_date,
    updated_at
from {{ source('postgres_raw', 'olist_order_items') }}
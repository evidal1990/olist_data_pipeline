{{ config(
    materialized = 'view'
) }}

select
    order_id,
    order_item_id,
    product_id,
    seller_id,
    cast(price as decimal(10, 2)) as price,
    cast(freight_value as decimal(10, 2)) as freight_value,
    shipping_limit_date
from {{ source('postgres_raw', 'olist_order_items') }}
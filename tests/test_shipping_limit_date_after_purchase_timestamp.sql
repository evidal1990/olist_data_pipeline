{{ config(severity='warn') }}

select
    orders_items.order_id,
    orders_items.order_item_id,
    orders_items.shipping_limit_date,
    orders.order_purchase_timestamp
from {{ ref('stg_orders_items') }} orders_items
join {{ ref('stg_orders') }} orders using (order_id)
where orders_items.shipping_limit_date < orders.order_purchase_timestamp

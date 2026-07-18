select
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_delivered_customer_date,
    _airbyte_extracted_at
from {{ source('postgres_raw', 'olist_orders') }}
-- where date(_airbyte_extracted_at) >= date_sub(current_date(), interval 7 day)
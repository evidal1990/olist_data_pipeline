{{ config(
    materialized = 'incremental', 
    unique_key = 'order_id',
    on_schema_change = 'fail'
) }}

select
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_delivered_customer_date,
    updated_at
from {{ source('postgres_raw', 'olist_orders') }}

{% if is_incremental() %}
where updated_at >= (select max(updated_at) from {{ this }})
{% endif %}
-- where date(_airbyte_extracted_at) >= date_sub(current_date(), interval 7 day)
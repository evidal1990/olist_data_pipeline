{{ config(
    materialized = 'incremental', 
    unique_key = 'product_id',
    on_schema_change = 'fail'
) }}

select
    product_id,
    product_category_name,
    cast(product_name_lenght as integer) as product_name_length,
    cast(product_description_lenght as integer) as product_description_length,
    cast(product_photos_qty as integer) as product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm,
    cast(updated_at as timestamp) as updated_at
from {{ source('postgres_raw', 'olist_products') }}

{% if is_incremental() %}
where cast(updated_at as timestamp) >= (select cast(max(updated_at) as timestamp) from {{ this }})
{% endif %}
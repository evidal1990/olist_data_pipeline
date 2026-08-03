{{ config(
    materialized = 'incremental', 
    unique_key = 'review_id',
    on_schema_change = 'fail'
) }}

select
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    cast(review_creation_date as datetime) as review_creation_date,
    review_answer_timestamp,
    cast(updated_at as timestamp) as updated_at
from {{ source('postgres_raw', 'olist_order_reviews') }}

{% if is_incremental() %}
where cast(updated_at as timestamp) >= (select cast(max(updated_at) as timestamp) from {{ this }})
{% endif %}
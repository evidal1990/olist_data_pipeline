{{ config(
    materialized = 'table'
) }}

select
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    cast(review_creation_date as datetime) as review_creation_date,
    review_answer_timestamp,
    updated_at
from {{ source('postgres_raw', 'olist_order_reviews') }}
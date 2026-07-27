select
    seller_id,
    seller_state
from {{ref('stg_sellers')}}
where seller_state not in(
    select state from {{ref('brazilian_states')}}
)
and seller_state is not null
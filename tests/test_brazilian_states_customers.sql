select
    customer_id,
    customer_state
from {{ref('stg_customers')}}
where customer_state not in(
    select state from {{ref('brazilian_states')}}
)
and customer_state is not null
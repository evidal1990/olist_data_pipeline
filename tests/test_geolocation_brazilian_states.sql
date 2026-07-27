select
    geolocation_zip_code_prefix,
    geolocation_state
from {{ref('stg_geolocation')}}
where geolocation_state not in(
    select state from {{ref('brazilian_states')}}
)
and geolocation_state is not null
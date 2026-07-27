{% test valid_city_for_state(model, column_name, state_column) %}

select *
from {{ model }} m
where {{ column_name }} is not null
and not exists (
    select 1
    from {{ ref('brazilian_cities') }} c
    where lower(c.cidade) = m.{{ column_name }}
      and c.estado = m.{{ state_column }}
)

{% endtest %}
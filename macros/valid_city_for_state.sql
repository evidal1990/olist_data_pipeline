{% macro _strip_accents(expr) -%}
translate(lower({{ expr }}), 'áàâãäéèêëíìîïóòôõöúùûüç', 'aaaaaeeeeiiiiooooouuuuc')
{%- endmacro %}

{% test valid_city_for_state(model, column_name, state_column) %}

-- O seed brazilian_cities guarda os nomes oficiais com acento (IBGE),
-- enquanto as fontes do Olist trazem as cidades sem acento.
-- A comparação ignora acentos dos dois lados.
select *
from {{ model }} m
where {{ column_name }} is not null
and not exists (
    select 1
    from {{ ref('brazilian_cities') }} c
    where {{ _strip_accents('c.cidade') }} = {{ _strip_accents('m.' ~ column_name) }}
      and c.estado = m.{{ state_column }}
)

{% endtest %}

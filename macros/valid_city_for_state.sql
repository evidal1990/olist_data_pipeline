{#
    Chave de comparação de nomes de cidade: minúsculas, sem acento,
    apóstrofo e hífen tratados como espaço e espaços repetidos reduzidos a um.
    Ex.: 'Itapejara D''Oeste' e 'itapejara d  oeste' -> 'itapejara d oeste'
         'Mogi-Guaçu' e 'mogi guacu' -> 'mogi guacu' (ADR-0002, D1)
#}
{% macro _city_key(expr) -%}
{#- apóstrofo como literal: no BigQuery '' não escapa aspas, então usamos "'" -#}
{%- set apostrophe = "chr(39)" if target.type == 'postgres' else '"\'"' -%}
{{ clean_text("replace(replace(translate(lower(" ~ expr ~ "), 'áàâãäéèêëíìîïóòôõöúùûüç', 'aaaaaeeeeiiiiooooouuuuc'), " ~ apostrophe ~ ", ' '), '-', ' ')") }}
{%- endmacro %}

{% test valid_city_for_state(model, column_name, state_column) %}

-- O seed brazilian_cities guarda os nomes oficiais com acento (IBGE),
-- enquanto as fontes do Olist trazem as cidades sem acento, às vezes com
-- o apóstrofo trocado por espaço (d'oeste -> d oeste).
-- A comparação ignora maiúsculas, acentos, apóstrofos e espaços repetidos.
select *
from {{ model }} m
where {{ column_name }} is not null
and not exists (
    select 1
    from {{ ref('brazilian_cities') }} c
    where {{ _city_key('c.cidade') }} = {{ _city_key('m.' ~ column_name) }}
      and c.estado = m.{{ state_column }}
)

{% endtest %}

{#
    City name comparison key: lowercase, no accents, apostrophes and hyphens
    treated as spaces, repeated spaces collapsed into one.
    Ex.: 'Itapejara D''Oeste' and 'itapejara d  oeste' -> 'itapejara d oeste'
         'Mogi-Guaçu' and 'mogi guacu'                -> 'mogi guacu' (ADR-0002, D1)

    Order matters: lower() runs before translate(), so the accent list only
    needs lowercase letters. The two translate() lists are matched by
    position and must keep the same length.
#}
{% macro _city_key(expr) -%}
{#- Apostrophe literal: BigQuery does not escape quotes with '', so we use "'". Postgres uses chr(39). -#}
{%- set apostrophe = "chr(39)" if target.type == 'postgres' else '"\'"' -%}
{{ clean_text("replace(replace(translate(lower(" ~ expr ~ "), 'áàâãäéèêëíìîïóòôõöúùûüç', 'aaaaaeeeeiiiiooooouuuuc'), " ~ apostrophe ~ ", ' '), '-', ' ')") }}
{%- endmacro %}

{#
    Test: valid_city_for_state

    Fails for every row whose city does not exist, in the row's state, in the
    brazilian_cities seed (official IBGE municipalities).

    Arguments:
    - column_name: city column being tested.
    - state_column: state (UF) column of the same model. Compared as is with
      the seed's `estado`, so it must hold the two-letter uppercase code.

    Behavior:
    - Rows with a null city are skipped; nulls are covered by not_null.
    - Returns the failing rows themselves, so --store-failures saves them for
      auditing.
    - The seed lists municipalities only. Districts and localities (e.g.
      Taguatinga/DF, Trancoso/BA) fail by design and are monitored, not
      fixed row by row (ADR-0002, D3).
#}
{% test valid_city_for_state(model, column_name, state_column) %}

-- The brazilian_cities seed stores official IBGE names with accents, while
-- the Olist sources bring city names without accents, sometimes with the
-- apostrophe replaced by a space (d'oeste -> d oeste) or with hyphens.
-- The comparison ignores case, accents, apostrophes, hyphens and repeated
-- spaces (see _city_key).
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

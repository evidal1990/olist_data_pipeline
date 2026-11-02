{#
    Padroniza texto livre vindo das fontes:
    - troca qualquer sequência de espaços, tabulações ou quebras de linha por um único espaço
    - remove os espaços das pontas
    Ex.: '  rio  de   janeiro ' -> 'rio de janeiro'
#}
{% macro clean_text(column) -%}
    {%- if target.type == 'postgres' -%}
        trim(regexp_replace({{ column }}, '\s+', ' ', 'g'))
    {%- else -%}
        trim(regexp_replace({{ column }}, r'\s+', ' '))
    {%- endif -%}
{%- endmacro %}

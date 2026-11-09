# Backlog: ADR-0002 (validação de cidade/UF da geolocalização)

- **ADR:** [0002-validacao-cidade-uf-por-cep-e-coordenadas.md](0002-validacao-cidade-uf-por-cep-e-coordenadas.md)
- **Status possíveis:** `To do` · `In progress` · `Done`
- **Como usar:** atualize a coluna **Status** do quadro. Os detalhes e critérios
de aceite de cada tarefa estão logo abaixo.

## Quadro

| ID | Tarefa | Decisão | Depende de | Status |
|---|---|---|---|---|
| T01 | Registrar a linha de base dos testes `valid_city_for_state` | D1, D2 | – | To do |
| T02 | Tratar hífen como espaço em `_city_key` | D1 | T01 | To do |
| T03 | Levantar os candidatos a alias | D2 | T02 | To do |
| T04 | Criar o seed `city_aliases` com testes | D2 | T03 | To do |
| T05 | Integrar `city_aliases` ao teste `valid_city_for_state` | D2 | T04 | To do |
| T06 | Criar o seed `cep_uf_ranges` com testes | D5 | – | To do |
| T07 | Configurar a camada intermediate | D5 | – | To do |
| T08 | Criar `int_geolocation_validated` | D4, D5, D6 | T04, T06, T07 | To do |
| T09 | Documentar e testar `int_geolocation_validated` | D5 | T08 | To do |
| T10 | Calibrar o limite de outlier (`geo_coord_outlier_km`) | D5 (questão aberta) | T08 | To do |
| T11 | Definir como monitorar a taxa de falha percentual | D3 (questão aberta) | T05 | To do |
| T12 | Rodar `dbt build` e atualizar os dashboards da staging | – | T05, T09 | To do |
| T13 | Atualizar a ADR-0002 (resultados e status **Aceita**) | – | T10, T11, T12 | To do |
| T14 | Abrir o PR da implementação | – | T13 | To do |

## Detalhes

### T01. Registrar a linha de base dos testes `valid_city_for_state`

Anotar as falhas atuais dos três testes que usam a macro: `geolocation_city`,
`customer_city` e `seller_city`. Sem essa referência não dá para medir o efeito
da D1 e da D2.

- **Aceite:** contagem de linhas e de pares cidade/UF por teste registrada
neste arquivo (seção "Medições"). Referência já conhecida:
`geolocation_city` = 5.199 linhas / 981 pares.

### T02. Tratar hífen como espaço em `_city_key`

Em `macros/valid_city_for_state.sql`, substituir `-` por espaço na chave, como
já é feito com o apóstrofo. Validar nos dois dialetos que a macro suporta
(`postgres` e `bigquery`).

- **Aceite:** `mogi-guacu`, `biritiba-mirim` e `mogi-mirim` deixam de falhar;
as falhas de `geolocation_city` caem cerca de 743 linhas; as quedas em
`customer_city` e `seller_city` são registradas em "Medições".

### T03. Levantar os candidatos a alias

Consultar os pares que ainda falham após a T02 e separar as **renomeações e
variações ortográficas oficiais** (ex.: `embu` → Embu das Artes, `parati` →
Paraty, `santana do livramento` → Sant'Ana do Livramento, `acu` → Assú) de
distritos e erros de digitação.

- **Aceite:** lista revisada em que cada alias tem uma fonte (IBGE ou lei de
renomeação). Distritos e erros de digitação ficam de fora, conforme o
critério da D2.

### T04. Criar o seed `city_aliases` com testes

`seeds/city_aliases.csv` com as colunas `nome_fonte`, `estado` e `cidade_ibge`,
mais a documentação no `schema.yml` dos seeds.

- **Testes:**
  - `unique_combination_of_columns` em (`nome_fonte`, `estado`);
  - `not_null` nas três colunas;
  - `cidade_ibge` + `estado` existem em `brazilian_cities`.
- **Aceite:** `dbt seed` e `dbt test --select city_aliases` passam.

### T05. Integrar `city_aliases` ao teste `valid_city_for_state`

Antes de comparar com `brazilian_cities`, o teste resolve o nome pelo alias
(`left join` em `city_aliases`, comparando pela mesma chave `_city_key`).

- **Aceite:** os nomes da T03 deixam de falhar nos três testes; as falhas
restantes são registradas em "Medições".

### T06. Criar o seed `cep_uf_ranges` com testes

`seeds/cep_uf_ranges.csv` com as colunas `cep_prefixo_inicio`,
`cep_prefixo_fim` e `estado`, usando as faixas oficiais dos Correios no
formato de prefixo de 5 dígitos. UFs com mais de uma faixa (AM, DF, GO) têm
uma linha por faixa.

- **Testes:**
  - as 27 UFs estão presentes;
  - `cep_prefixo_inicio <= cep_prefixo_fim`;
  - nenhuma faixa se sobrepõe a outra.
- **Aceite:** todos os prefixos de `stg_geolocation` caem em exatamente uma
faixa.

### T07. Configurar a camada intermediate

Definir a materialização da camada intermediate (sugestão: `view`).

- **Atenção:** o `dbt_project.yml` está no `.gitignore`, então uma
configuração feita nele não fica versionada. Alternativas: definir com
`{{ config(...) }}` no próprio modelo ou rever esse item do `.gitignore`.
- **Aceite:** a decisão está registrada e a configuração está aplicada de
forma reproduzível.

### T08. Criar `int_geolocation_validated`

`models/intermediate/int_geolocation_validated.sql`, no mesmo grão de
`stg_geolocation`, com as colunas da D5:

- `uf_from_cep`, `is_uf_consistent`;
- `is_coord_in_brazil`;
- `coord_distance_km_to_cep_median`, `is_coord_outlier` (mediana por CEP,
conforme a D6, e `var('geo_coord_outlier_km', 50)`);
- `city_ibge`, `is_city_ibge_municipality`;
- `geo_quality_status`.
- **Aceite:** o número de linhas é igual ao de `stg_geolocation`, e a
distribuição de `geo_quality_status` é coerente com a análise da ADR
(ex.: cerca de 115 linhas `coord_suspeita` no grupo "outra UF").

### T09. Documentar e testar `int_geolocation_validated`

Escrever o `schema.yml` do modelo com a descrição de cada flag e a regra que a
define.

- **Testes:**
  - `accepted_values` em `geo_quality_status`;
  - `not_null` em `uf_from_cep`;
  - igualdade de contagem com `stg_geolocation`;
  - `is_uf_consistent = true` com severidade `warn`.
- **Aceite:** `dbt build --select int_geolocation_validated` passa.

### T10. Calibrar o limite de outlier (`geo_coord_outlier_km`)

Analisar a distribuição de `coord_distance_km_to_cep_median` (percentis, CEPs
rurais e urbanos) e escolher o valor do limite.

- **Aceite:** o valor escolhido e a justificativa estão registrados na
ADR-0002, e a `var` foi atualizada se necessário.

### T11. Definir como monitorar a taxa de falha percentual

Escolher entre um parâmetro de taxa máxima no teste customizado ou o
acompanhamento da taxa (falhas / total) no dashboard da staging.

- **Aceite:** a opção escolhida está implementada e registrada na ADR-0002.

### T12. Rodar `dbt build` e atualizar os dashboards da staging

Rodar `dbt build` completo e atualizar os dois dashboards da staging com os
novos resultados.

- **Aceite:** o build termina sem erro e os dois dashboards refletem as novas
contagens.

### T13. Atualizar a ADR-0002 (resultados e status **Aceita**)

Incluir um adendo com os números finais (antes/depois), o limite calibrado e a
decisão de monitoramento. Depois, mudar o status para **Aceita**.

- **Aceite:** a ADR reflete o que foi de fato implementado.

### T14. Abrir o PR da implementação

Branch sugerida: `feat/int-geolocation-validated`.

- **Aceite:** o PR referencia a ADR-0002 e este backlog e mostra as medições
antes/depois.

## Medições

| Teste | Linha de base (T01) | Após D1 (T02) | Após D2 (T05) |
|---|---|---|---|
| `stg_geolocation.geolocation_city` | 5.199 linhas / 981 pares | | |
| `stg_customers.customer_city` | | | |
| `stg_sellers.seller_city` | | | |

## Fora do escopo

- **D7:** malha municipal do IBGE com `ST_CONTAINS`.
- `int_geolocation_by_zip` **(ADR-0001):** passa a usar a mediana da D6 e
pode ser construído sobre `int_geolocation_validated` em uma tarefa
separada.

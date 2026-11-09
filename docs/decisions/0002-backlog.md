# Backlog: ADR-0002 (validação de cidade/UF da geolocalização)

- **ADR:** [0002-validacao-cidade-uf-por-cep-e-coordenadas.md](0002-validacao-cidade-uf-por-cep-e-coordenadas.md)
- **Status possíveis:** `To do` · `In progress` · `Done`
- **Como usar:** atualize a coluna **Status** do quadro. Cada tarefa tem, logo
abaixo, **O que** fazer, o critério de **Aceite** e a **Evidência**. Ao concluir
uma tarefa, troque _Pendente_ pela evidência (números, consultas, commits).

## Quadro

| ID | Tarefa | Decisão | Depende de | Status |
|---|---|---|---|---|
| T01 | Registrar a linha de base dos testes `valid_city_for_state` | D1, D2 | – | Done |
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

#### O que

Anotar as falhas atuais dos três testes que usam a macro:
`geolocation_city`, `customer_city` e `seller_city`. Sem essa referência não dá
para medir o efeito da D1 e da D2.

#### Aceite

Contagem de linhas e de pares cidade/UF por teste registrada neste
arquivo (seção "Medições").

#### Evidência

| Teste | Linhas com falha | Pares cidade/UF | Taxa |
|---|---|---|---|
| `geolocation_city` | 5.199 | 981 | 0,70% de 738.016 |
| `customer_city` | 2.268 | 292 | 0,72% de 314.000 |
| `seller_city` | 290 | 95 | 3,41% de 8.500 |

##### Fonte

- **Linhas com falha:** execução de
  `dbt test --select "test_name:valid_city_for_state"` (`PASS=0 WARN=3 ERROR=0`).
- **Pares cidade/UF:** SQL compilado de cada teste
  (`target/compiled/.../schema.yml/valid_city_for_state_*.sql`), executado no
  BigQuery com `COUNT(DISTINCT cidade || '|' || uf)`.

##### Data dos dados

2026-11-08 às 21:19 (horário de Brasília), com o código da `main` em `36b13c4`,
que já inclui a remoção de espaços extras dos nomes (`5d33b0d`). Os números são
iguais aos das tabelas de auditoria `postgres_staging_dbt_test__audit`
(gravadas em 2026-11-02 às 19:58), que esta execução não regravou porque não
usou `--store-failures`.

##### Taxa

Calculada sobre o total de linhas atual de cada modelo da staging.

##### Observação

A taxa de `seller_city` é quase 5 vezes maior que a das outras tabelas. Vale
reavaliar depois da T02.

### T02. Tratar hífen como espaço em `_city_key`

#### O que

Em `macros/valid_city_for_state.sql`, substituir `-` por espaço na
chave, como já é feito com o apóstrofo. Validar nos dois dialetos que a macro
suporta (`postgres` e `bigquery`).

#### Aceite

`mogi-guacu`, `biritiba-mirim` e `mogi-mirim` deixam de falhar; as
falhas de `geolocation_city` caem cerca de 743 linhas; as quedas em
`customer_city` e `seller_city` são registradas em "Medições".

#### Evidência

_Pendente._

### T03. Levantar os candidatos a alias

#### O que

Consultar os pares que ainda falham após a T02 e separar as
**renomeações e variações ortográficas oficiais** (ex.: `embu` → Embu das Artes,
`parati` → Paraty, `santana do livramento` → Sant'Ana do Livramento, `acu` →
Assú) de distritos e erros de digitação.

#### Aceite

Lista revisada em que cada alias tem uma fonte (IBGE ou lei de
renomeação). Distritos e erros de digitação ficam de fora, conforme o critério
da D2.

#### Evidência

_Pendente._

### T04. Criar o seed `city_aliases` com testes

#### O que

Criar `seeds/city_aliases.csv` com as colunas `nome_fonte`, `estado`
e `cidade_ibge`, mais a documentação no `schema.yml` dos seeds. Testes:

- `unique_combination_of_columns` em (`nome_fonte`, `estado`);
- `not_null` nas três colunas;
- `cidade_ibge` + `estado` existem em `brazilian_cities`.

#### Aceite

`dbt seed` e `dbt test --select city_aliases` passam.

#### Evidência

_Pendente._

### T05. Integrar `city_aliases` ao teste `valid_city_for_state`

#### O que

Antes de comparar com `brazilian_cities`, o teste resolve o nome pelo
alias (`left join` em `city_aliases`, comparando pela mesma chave `_city_key`).

#### Aceite

Os nomes da T03 deixam de falhar nos três testes; as falhas
restantes são registradas em "Medições".

#### Evidência

_Pendente._

### T06. Criar o seed `cep_uf_ranges` com testes

#### O que

Criar `seeds/cep_uf_ranges.csv` com as colunas `cep_prefixo_inicio`,
`cep_prefixo_fim` e `estado`, usando as faixas oficiais dos Correios no formato
de prefixo de 5 dígitos. UFs com mais de uma faixa (AM, DF, GO) têm uma linha
por faixa. Testes:

- as 27 UFs estão presentes;
- `cep_prefixo_inicio <= cep_prefixo_fim`;
- nenhuma faixa se sobrepõe a outra.

#### Aceite

Todos os prefixos de `stg_geolocation` caem em exatamente uma faixa.

#### Evidência

_Pendente._

### T07. Configurar a camada intermediate

#### O que

Definir a materialização da camada intermediate (sugestão: `view`).

Atenção: o `dbt_project.yml` está no `.gitignore`, então uma configuração feita
nele não fica versionada. Alternativas: definir com `{{ config(...) }}` no
próprio modelo ou rever esse item do `.gitignore`.

#### Aceite

A decisão está registrada e a configuração está aplicada de forma
reproduzível.

#### Evidência

_Pendente._

### T08. Criar `int_geolocation_validated`

#### O que

Criar `models/intermediate/int_geolocation_validated.sql`, no mesmo
grão de `stg_geolocation`, com as colunas da D5:

- `uf_from_cep`, `is_uf_consistent`;
- `is_coord_in_brazil`;
- `coord_distance_km_to_cep_median`, `is_coord_outlier` (mediana por CEP,
  conforme a D6, e `var('geo_coord_outlier_km', 50)`);
- `city_ibge`, `is_city_ibge_municipality`;
- `geo_quality_status`.

#### Aceite

O número de linhas é igual ao de `stg_geolocation`, e a
distribuição de `geo_quality_status` é coerente com a análise da ADR (ex.: cerca
de 115 linhas `coord_suspeita` no grupo "outra UF").

#### Evidência

_Pendente._

### T09. Documentar e testar `int_geolocation_validated`

#### O que

Escrever o `schema.yml` do modelo com a descrição de cada flag e a
regra que a define. Testes:

- `accepted_values` em `geo_quality_status`;
- `not_null` em `uf_from_cep`;
- igualdade de contagem com `stg_geolocation`;
- `is_uf_consistent = true` com severidade `warn`.

#### Aceite

`dbt build --select int_geolocation_validated` passa.

#### Evidência

_Pendente._

### T10. Calibrar o limite de outlier (`geo_coord_outlier_km`)

#### O que

Analisar a distribuição de `coord_distance_km_to_cep_median`
(percentis, CEPs rurais e urbanos) e escolher o valor do limite.

#### Aceite

O valor escolhido e a justificativa estão registrados na ADR-0002, e
a `var` foi atualizada se necessário.

#### Evidência

_Pendente._

### T11. Definir como monitorar a taxa de falha percentual

#### O que

Escolher entre um parâmetro de taxa máxima no teste customizado ou o
acompanhamento da taxa (falhas / total) no dashboard da staging.

#### Aceite

A opção escolhida está implementada e registrada na ADR-0002.

#### Evidência

_Pendente._

### T12. Rodar `dbt build` e atualizar os dashboards da staging

#### O que

Rodar `dbt build` completo e atualizar os dois dashboards da staging
com os novos resultados.

#### Aceite

O build termina sem erro e os dois dashboards refletem as novas
contagens.

#### Evidência

_Pendente._

### T13. Atualizar a ADR-0002 (resultados e status **Aceita**)

#### O que

Incluir na ADR um adendo com os números finais (antes/depois), o
limite calibrado e a decisão de monitoramento. Depois, mudar o status para
**Aceita**.

#### Aceite

A ADR reflete o que foi de fato implementado.

#### Evidência

_Pendente._

### T14. Abrir o PR da implementação

#### O que

Abrir o PR da implementação. Branch sugerida:
`feat/int-geolocation-validated`.

#### Aceite

O PR referencia a ADR-0002 e este backlog e mostra as medições
antes/depois.

#### Evidência

_Pendente._

## Medições

| Teste | Linha de base (T01) | Após D1 (T02) | Após D2 (T05) |
|---|---|---|---|
| `stg_geolocation.geolocation_city` | 5.199 linhas / 981 pares (0,70% de 738.016) | | |
| `stg_customers.customer_city` | 2.268 linhas / 292 pares (0,72% de 314.000) | | |
| `stg_sellers.seller_city` | 290 linhas / 95 pares (3,41% de 8.500) | | |

Fonte e data da linha de base: ver a evidência da T01.

## Fora do escopo

- **D7:** malha municipal do IBGE com `ST_CONTAINS`.
- `int_geolocation_by_zip` **(ADR-0001):** passa a usar a mediana da D6 e
pode ser construído sobre `int_geolocation_validated` em uma tarefa
separada.

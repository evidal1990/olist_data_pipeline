# Backlog: ADR-0002 (validação de cidade/UF da geolocalização)

- **ADR:** [0002-validacao-cidade-uf-por-cep-e-coordenadas.md](0002-validacao-cidade-uf-por-cep-e-coordenadas.md)
- **Status possíveis:** `To do` · `In progress` · `Done`
- **Como usar:** atualize a coluna **Status** do quadro. Ao concluir uma
tarefa, acrescente em "Detalhes" o **Passo a passo** e o **Resultado**.

## Quadro

| ID | O que | Decisão | Depende de | Como | Resultado | Status |
|---|---|---|---|---|---|---|
| T01 | Medir as falhas antes de qualquer correção | D1, D2 | – | `dbt test` nos 3 testes de cidade; pares contados no BigQuery | geo 5.199, customers 2.268, sellers 290 linhas | Done |
| T02 | Fazer `mogi-guacu` bater com "Mogi Guaçu" | D1 | T01 | `replace(..., '-', ' ')` na macro; testado no BigQuery e no Postgres | geo −743 (4.456), customers −350 (1.918), sellers −6 (284) | Done |
| T03 | Separar o que vale mapear do que é ruído da fonte | D2 | T02 | Pares que somam 80% das falhas (286 de 996) comparados com o seed do IBGE e revisados um a um | 37 aliases + `piumhii`, regras R1–R3 (D8); projeção de 4.547 falhas restantes | Done |
| T04 | Guardar os aliases e as regiões do DF | D2, D8 | T03 | CSV com `nome_fonte`, `estado`, `cidade_ibge`, `tipo`; testes de unicidade e de destino no IBGE | – | To do |
| T05 | Fazer o teste reconhecer aliases e regras | D2, D8 | T04 | Macro compartilhada com R1/R2 e `left join` no seed antes da comparação | – | To do |
| T06 | Saber a UF a partir do CEP | D5 | – | CSV com as faixas dos Correios; testes de cobertura e sobreposição | – | To do |
| T07 | Definir a materialização da nova camada | D5 | – | `config()` no modelo ou rever o `dbt_project.yml` no `.gitignore` | – | To do |
| T08 | Marcar a qualidade de cada linha de geolocalização | D4, D5, D6 | T04, T06, T07 | Flags de UF pelo CEP, coordenada contra a mediana do CEP e cidade no IBGE | – | To do |
| T09 | Garantir que o modelo é confiável | D5 | T08 | `schema.yml` com cada flag e testes de valores e contagem | – | To do |
| T10 | Escolher o limite de distância | D5 (questão aberta) | T08 | Percentis de `coord_distance_km_to_cep_median` | – | To do |
| T11 | Alertar por taxa, não por contagem | D3 (questão aberta) | T05 | Parâmetro no teste ou acompanhamento no dashboard | – | To do |
| T12 | Validar tudo junto | – | T05, T09 | `dbt build` completo e atualização dos dois dashboards | – | To do |
| T13 | Registrar o que foi implementado | – | T10, T11, T12 | Adendo com números finais e mudança de status | – | To do |
| T14 | Revisar a implementação | – | T13 | PR referenciando a ADR e o backlog | – | To do |

## Detalhes

Tarefas concluídas têm **O que**, **Passo a passo** e **Resultado**. As
pendentes têm só **O que**; o passo a passo entra quando forem feitas.

### T01. Registrar a linha de base dos testes `valid_city_for_state`

#### O que

Medir as falhas dos três testes que usam a macro (`geolocation_city`,
`customer_city` e `seller_city`) antes de qualquer correção, para medir o
efeito da D1 e da D2.

#### Passo a passo

1. Criar a branch `chore/adr-0002-t01-city-tests-baseline` a partir da `main`
   (`36b13c4`).
2. Ler as tabelas de auditoria `postgres_staging_dbt_test__audit.valid_city_for_state_*`
   no BigQuery. Elas eram de 2026-11-02 às 19:58, e não era possível confirmar
   se já incluíam o commit `5d33b0d` (remoção de espaços extras).
3. Para tirar a dúvida, rodar só os três testes:
   `dbt test --select "test_name:valid_city_for_state"` (`PASS=0 WARN=3 ERROR=0`).
4. Contar os pares cidade/UF distintos rodando no BigQuery o SQL compilado de
   cada teste (`target/compiled/.../valid_city_for_state_*.sql`) com
   `COUNT(DISTINCT cidade || '|' || uf)`.
5. Calcular a taxa sobre o total de linhas atual de cada modelo da staging.
6. Atualizar os dois dashboards da staging com a execução.

#### Resultado

Medido em 2026-11-08 às 21:19 (horário de Brasília). Os números foram iguais aos
das tabelas de auditoria de 02/11.

| Teste | Linhas com falha | Pares cidade/UF | Taxa |
|---|---|---|---|
| `geolocation_city` | 5.199 | 981 | 0,70% de 738.016 |
| `customer_city` | 2.268 | 292 | 0,72% de 314.000 |
| `seller_city` | 290 | 95 | 3,41% de 8.500 |

A taxa de `seller_city` é quase 5 vezes a das outras tabelas.

### T02. Tratar hífen como espaço em `_city_key`

#### O que

Fazer a comparação de nomes tratar `-` como espaço, para que `mogi-guacu` bata
com "Mogi Guaçu" do IBGE.

#### Passo a passo

1. Criar a branch `fix/adr-0002-t02-city-key-hyphen`.
2. Em `macros/valid_city_for_state.sql`, acrescentar `replace(..., '-', ' ')`
   em `_city_key`, depois do tratamento do apóstrofo.
3. Rodar `dbt test --select "test_name:valid_city_for_state"` no BigQuery
   (`PASS=0 WARN=3 ERROR=0`).
4. No SQL compilado de cada teste, contar os pares, conferir que `mogi-guacu`,
   `biritiba-mirim` e `mogi-mirim` saíram das falhas e listar os nomes com
   hífen que continuam falhando.
5. Validar o dialeto Postgres: o projeto não tem target Postgres, então a
   expressão gerada foi testada com `SELECT` em valores de exemplo no
   container `olistdb` (Postgres 16).
6. Rodar os testes de novo com `--store-failures`, para que as tabelas de
   auditoria mostrem as falhas atuais.
7. Atualizar os dois dashboards da staging.

#### Resultado

Medido em 2026-11-08 às 21:28 (horário de Brasília); as tabelas de auditoria
foram regravadas às 21:30, com os mesmos números.

| Teste | Antes (T01) | Depois | Diferença |
|---|---|---|---|
| `geolocation_city` | 5.199 linhas / 981 pares | 4.456 linhas / 963 pares | −743 linhas / −18 pares |
| `customer_city` | 2.268 linhas / 292 pares | 1.918 linhas / 286 pares | −350 linhas / −6 pares |
| `seller_city` | 290 linhas / 95 pares | 284 linhas / 93 pares | −6 linhas / −2 pares |

### T03. Levantar os candidatos a alias

#### O que

Separar, entre as falhas que restam, as renomeações e grafias oficiais (que
valem um alias) dos distritos e erros de digitação (ruído da fonte).

#### Passo a passo

1. Criar a branch `chore/adr-0002-t03-city-alias-candidates`.
2. Juntar as falhas dos três testes depois da T02 (6.658 linhas, 996 pares
   cidade/UF) a partir das tabelas de auditoria de 21:30.
3. Ordenar os pares por quantidade de linhas e recortar os que somam 80% das
   falhas: 286 pares. Os outros 710 ficam como cauda longa (D3).
4. Comparar cada par com o seed `brazilian_cities` da mesma UF, por nome
   parecido e por nome contido em outro, para sugerir candidatos.
5. Revisar os 286 pares um a um e classificar em: alias, padrão sistemático
   (regra), distrito ou localidade, erro de digitação, cidade de outra UF.
6. Conferir que cada nome de destino existe no seed, na mesma UF.
7. Calcular o efeito de cada grupo sobre todas as falhas, não só sobre o
   recorte.
8. Levar à decisão os casos fora do critério da D2 (as regras e `piumhii`) e
   registrar o resultado no adendo de 2026-11-08 da ADR-0002.

#### Resultado

| Grupo | Linhas (geo / clientes / vendedores) | Total | Tratamento |
|---|---|---|---|
| Alias (renomeação ou grafia oficial) | 1.290 / 264 / 7 | 1.561 (23,4%) | Seed `city_aliases` (T04) |
| Alias por exceção: `piumhii` | 98 / 85 / 0 | 183 (2,7%) | Seed `city_aliases` (T04), D2 revisada |
| Regra R1: UF colada no nome | 5 / 0 / 31 | 36 (0,5%) | Regra no teste (T05), D8 |
| Regra R2: "cidade, estado, brasil" | 2 / 0 / 9 | 11 (0,2%) | Regra no teste (T05), D8 |
| Regra R3: região administrativa do DF | 287 / 28 / 5 | 320 (4,8%) | 35 regiões no seed `city_aliases` (T04), D8 |
| Fora: distritos, localidades, erros de digitação, UF errada | 2.774 / 1.541 / 232 | 4.547 (68,3%) | Monitorar (D3) |
| **Total** | 4.456 / 1.918 / 284 | 6.658 | |

**Aliases.** 37 candidatos, mais a exceção `piumhii` → piumhi (MG). O nome
oficial é o do seed (IBGE); o tipo foi classificado pelo Claude, sem consultar
os atos legais de renomeação. "do oeste" no lugar de "d'Oeste" ficou como
alias, e não como regra, porque existem municípios oficiais com "do Oeste"
(ex.: São Miguel do Oeste/SC).

| Nome na fonte | UF | Nome IBGE (seed) | Tipo | Geo | Clientes | Vendedores |
|---|---|---|---|---|---|---|
| `santana do livramento` | RS | sant'ana do livramento | Grafia oficial diferente | 306 | 59 | 0 |
| `embu` | SP | embu das artes | Renomeação | 285 | 31 | 0 |
| `parati` | RJ | paraty | Grafia oficial diferente | 153 | 35 | 0 |
| `bom jesus` | GO | bom jesus de goiás | Nome abreviado | 53 | 28 | 0 |
| `acu` | RN | assú | Grafia oficial diferente | 61 | 6 | 0 |
| `espigao do oeste` | RO | espigão d'oeste | Grafia oficial diferente | 45 | 18 | 0 |
| `santa isabel do para` | PA | santa izabel do pará | Grafia oficial diferente | 42 | 21 | 0 |
| `brasopolis` | MG | brazópolis | Grafia oficial diferente | 47 | 9 | 0 |
| `armacao de buzios` | RJ | armação dos búzios | Grafia oficial diferente | 34 | 0 | 0 |
| `buzios` | RJ | armação dos búzios | Nome abreviado | 26 | 0 | 0 |
| `sao luis do paraitinga` | SP | são luiz do paraitinga | Grafia oficial diferente | 18 | 8 | 0 |
| `sao thome das letras` | MG | são tomé das letras | Grafia oficial diferente | 19 | 7 | 0 |
| `eldorado dos carajas` | PA | eldorado do carajás | Grafia oficial diferente | 22 | 0 | 0 |
| `amparo da serra` | MG | amparo do serra | Grafia oficial diferente | 13 | 3 | 0 |
| `florinia` | SP | florínea | Grafia oficial diferente | 14 | 2 | 0 |
| `santa barbara doeste` | SP | santa bárbara d'oeste | Grafia oficial diferente | 15 | 0 | 0 |
| `couto de magalhaes` | TO | couto magalhães | Grafia oficial diferente | 6 | 7 | 0 |
| `santo antonio do leverger` | MT | santo antônio de leverger | Grafia oficial diferente | 11 | 2 | 0 |
| `picarras` | SC | balneário piçarras | Renomeação | 9 | 1 | 2 |
| `santa rita do ibitipoca` | MG | santa rita de ibitipoca | Grafia oficial diferente | 7 | 5 | 0 |
| `barao de monte alto` | MG | barão do monte alto | Grafia oficial diferente | 11 | 0 | 0 |
| `santa teresinha` | BA | santa terezinha | Grafia oficial diferente | 6 | 5 | 0 |
| `dias davila` | BA | dias d'ávila | Grafia oficial diferente | 9 | 0 | 0 |
| `gouvea` | MG | gouveia | Grafia oficial diferente | 9 | 0 | 0 |
| `jequirica` | BA | jiquiriçá | Grafia oficial diferente | 9 | 0 | 0 |
| `lagoa do itaenga` | PE | lagoa de itaenga | Grafia oficial diferente | 9 | 0 | 0 |
| `trajano de morais` | RJ | trajano de moraes | Grafia oficial diferente | 9 | 0 | 0 |
| `bataipora` | MS | batayporã | Grafia oficial diferente | 2 | 6 | 0 |
| `planaltina de goias` | GO | planaltina | Nome alternativo | 2 | 6 | 0 |
| `itapage` | CE | itapajé | Grafia oficial diferente | 5 | 2 | 0 |
| `sao jorge do oeste` | PR | são jorge d'oeste | Grafia oficial diferente | 4 | 3 | 0 |
| `iguaraci` | PE | iguaracy | Grafia oficial diferente | 6 | 0 | 0 |
| `itabirinha de mantena` | MG | itabirinha | Renomeação | 6 | 0 | 0 |
| `sao luiz` | RR | são luiz do anauá | Nome abreviado | 6 | 0 | 0 |
| `sao valerio da natividade` | TO | são valério | Renomeação | 6 | 0 | 0 |
| `alta floresta do oeste` | RO | alta floresta d'oeste | Grafia oficial diferente | 5 | 0 | 0 |
| `paincandu` | PR | paiçandu | Grafia oficial diferente | 0 | 0 | 5 |

**Decisões tomadas** (adendo de 2026-11-08 da ADR-0002):

1. **Regras R1, R2 e R3** entram como a nova decisão D8. A R3 virou uma lista
   fechada das 35 regiões administrativas do DF no seed `city_aliases`, para o
   teste não depender do CEP e uma linha com a UF errada continuar falhando.
   Com a lista, R3 resolve 320 linhas (ficam de fora `riacho fundo 2` e
   `ceilandia norte`).
2. **`piumhii`** entra como exceção ao critério da D2, com tipo
   `erro_digitacao_sistematico`. Os outros erros de digitação têm 6 linhas ou
   menos e ficam fora.

### T04. Criar o seed `city_aliases` com testes

#### O que

Criar `seeds/city_aliases.csv` com as colunas `nome_fonte`, `estado`,
`cidade_ibge` e `tipo`, mais a documentação no `schema.yml` dos seeds. O
conteúdo vem da T03: os 37 aliases, `piumhii` (exceção) e as 35 regiões
administrativas do DF com destino Brasília (R3). Testes:

- `unique_combination_of_columns` em (`nome_fonte`, `estado`);
- `not_null` nas colunas;
- `cidade_ibge` + `estado` existem em `brazilian_cities`.

### T05. Integrar `city_aliases` e as regras R1/R2 ao teste `valid_city_for_state`

#### O que

Antes de comparar com `brazilian_cities`, o teste aplica as regras R1 (UF
colada no nome) e R2 ("cidade, estado, brasil") e resolve o nome pelo alias
(`left join` em `city_aliases`, comparando pela mesma chave `_city_key`). R1 e
R2 ficam numa macro compartilhada, que a T08 reutiliza.

### T06. Criar o seed `cep_uf_ranges` com testes

#### O que

Criar `seeds/cep_uf_ranges.csv` com as colunas `cep_prefixo_inicio`,
`cep_prefixo_fim` e `estado`, usando as faixas oficiais dos Correios no formato
de prefixo de 5 dígitos. UFs com mais de uma faixa (AM, DF, GO) têm uma linha
por faixa. Testes:

- as 27 UFs estão presentes;
- `cep_prefixo_inicio <= cep_prefixo_fim`;
- nenhuma faixa se sobrepõe a outra;
- todos os prefixos de `stg_geolocation` caem em exatamente uma faixa.

### T07. Configurar a camada intermediate

#### O que

Definir a materialização da camada intermediate (sugestão: `view`). O
`dbt_project.yml` está no `.gitignore`, então uma configuração feita nele não
fica versionada: usar `{{ config(...) }}` no próprio modelo ou rever esse item
do `.gitignore`.

### T08. Criar `int_geolocation_validated`

#### O que

Criar `models/intermediate/int_geolocation_validated.sql`, no mesmo grão de
`stg_geolocation`, com as colunas da D5:

- `uf_from_cep`, `is_uf_consistent`;
- `is_coord_in_brazil`;
- `coord_distance_km_to_cep_median`, `is_coord_outlier` (mediana por CEP,
  conforme a D6, e `var('geo_coord_outlier_km', 50)`);
- `city_ibge`, `is_city_ibge_municipality`;
- `geo_quality_status`.

### T09. Documentar e testar `int_geolocation_validated`

#### O que

Escrever o `schema.yml` do modelo com a descrição de cada flag e a regra que a
define. Testes:

- `accepted_values` em `geo_quality_status`;
- `not_null` em `uf_from_cep`;
- igualdade de contagem com `stg_geolocation`;
- `is_uf_consistent = true` com severidade `warn`.

### T10. Calibrar o limite de outlier (`geo_coord_outlier_km`)

#### O que

Analisar a distribuição de `coord_distance_km_to_cep_median` (percentis, CEPs
rurais e urbanos), escolher o valor do limite e registrá-lo na ADR-0002.

### T11. Definir como monitorar a taxa de falha percentual

#### O que

Escolher entre um parâmetro de taxa máxima no teste customizado ou o
acompanhamento da taxa (falhas / total) no dashboard da staging.

### T12. Rodar `dbt build` e atualizar os dashboards da staging

#### O que

Rodar `dbt build` completo e atualizar os dois dashboards da staging com os
novos resultados.

### T13. Atualizar a ADR-0002 (resultados e status **Aceita**)

#### O que

Incluir na ADR um adendo com os números finais (antes/depois), o limite
calibrado e a decisão de monitoramento. Depois, mudar o status para **Aceita**.

### T14. Abrir o PR da implementação

#### O que

Abrir o PR da implementação, referenciando a ADR-0002 e este backlog e com as
medições antes/depois. Branch sugerida: `feat/int-geolocation-validated`.

## Medições

| Teste | Linha de base (T01) | Após D1 (T02) | Após D2 (T05) |
|---|---|---|---|
| `stg_geolocation.geolocation_city` | 5.199 linhas / 981 pares (0,70% de 738.016) | 4.456 linhas / 963 pares (0,60%) | |
| `stg_customers.customer_city` | 2.268 linhas / 292 pares (0,72% de 314.000) | 1.918 linhas / 286 pares (0,61%) | |
| `stg_sellers.seller_city` | 290 linhas / 95 pares (3,41% de 8.500) | 284 linhas / 93 pares (3,34%) | |

Fonte e data de cada medição: ver o passo a passo da T01 e da T02.

## Fora do escopo

- **D7:** malha municipal do IBGE com `ST_CONTAINS`.
- `int_geolocation_by_zip` **(ADR-0001):** passa a usar a mediana da D6 e
pode ser construído sobre `int_geolocation_validated` em uma tarefa
separada.

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
| T02 | Tratar hífen como espaço em `_city_key` | D1 | T01 | Done |
| T03 | Levantar os candidatos a alias | D2 | T02 | Done |
| T04 | Criar o seed `city_aliases` com testes | D2, D8 | T03 | To do |
| T05 | Integrar `city_aliases` e as regras R1/R2 ao teste `valid_city_for_state` | D2, D8 | T04 | To do |
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

| Teste | Antes (T01) | Depois | Diferença |
|---|---|---|---|
| `geolocation_city` | 5.199 linhas / 981 pares | 4.456 linhas / 963 pares | −743 linhas / −18 pares |
| `customer_city` | 2.268 linhas / 292 pares | 1.918 linhas / 286 pares | −350 linhas / −6 pares |
| `seller_city` | 290 linhas / 95 pares | 284 linhas / 93 pares | −6 linhas / −2 pares |

##### Fonte

- **Mudança:** `_city_key` em `macros/valid_city_for_state.sql` passou a aplicar
  `replace(..., '-', ' ')` depois do tratamento do apóstrofo.
- **Linhas com falha:** execução de
  `dbt test --select "test_name:valid_city_for_state"` (`PASS=0 WARN=3 ERROR=0`).
- **Pares, hífens restantes e nomes-alvo:** SQL compilado de cada teste,
  executado no BigQuery.
- **Dialeto Postgres:** o projeto não tem target Postgres. A expressão gerada
  para o Postgres foi testada com `SELECT` em valores de exemplo no container
  `olistdb` (Postgres 16): `Mogi-Guaçu` e `mogi guacu` geram a mesma chave
  (`mogi guacu`), e `Itapejara D'Oeste` continua gerando `itapejara d oeste`.

##### Data dos dados

2026-11-08 às 21:28 (horário de Brasília). Os testes foram rodados de novo às
21:30 com `--store-failures`, com os mesmos números, para que as tabelas de
auditoria `postgres_staging_dbt_test__audit.valid_city_for_state_*` mostrem as
falhas atuais.

##### Resultado do aceite

- `mogi-guacu`, `biritiba-mirim` e `mogi-mirim` não aparecem mais nas falhas.
- A queda em `geolocation_city` foi de exatamente 743 linhas e 18 pares, o
  previsto na análise da ADR-0002.

##### Observação

As linhas com hífen que continuam falhando (13 em geolocalização, 1 em clientes
e 14 em vendedores) não são falha da correção:

- **Distritos e localidades:** `bacaxa (saquarema) - distrito`,
  `monte gordo (camacari) - distrito`, `colônia z-3`, `vau-acu`.
- **UF colada no nome:** `sao paulo - sp` (8), `andira-pr` (4), `lages - sc`
  (2), `guarulhos-sp`, `venda nova do imigrante-es`. É um padrão sistemático,
  principalmente em vendedores, que vale avaliar na T03 como regra (remover o
  sufixo de UF), e não como alias.


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

##### Escopo

- **Base:** falhas dos três testes depois da T02 (6.658 linhas, 996 pares
  cidade/UF somando os três testes).
- **Recorte:** os 286 pares que somam 80% das linhas com falha foram
  classificados um a um. Os 710 restantes ficam como cauda longa (D3).
- **Método:** cada par foi comparado com o seed `brazilian_cities` da mesma UF
  (similaridade de texto e nome contido em outro). Depois, cada caso foi
  revisado manualmente e classificado.

##### Resultado

| Grupo | Linhas (geo / clientes / vendedores) | Total | Tratamento |
|---|---|---|---|
| Alias (renomeação ou grafia oficial) | 1.290 / 264 / 7 | 1.561 (23,4%) | Seed `city_aliases` (T04) |
| Alias por exceção: `piumhii` | 98 / 85 / 0 | 183 (2,7%) | Seed `city_aliases` (T04), D2 revisada |
| Regra R1: UF colada no nome | 5 / 0 / 31 | 36 (0,5%) | Regra no teste (T05), D8 |
| Regra R2: "cidade, estado, brasil" | 2 / 0 / 9 | 11 (0,2%) | Regra no teste (T05), D8 |
| Regra R3: região administrativa do DF | 287 / 28 / 5 | 320 (4,8%) | 35 regiões no seed `city_aliases` (T04), D8 |
| Fora: distritos, localidades, erros de digitação, UF errada | 2.774 / 1.541 / 232 | 4.547 (68,3%) | Monitorar (D3) |
| **Total** | 4.456 / 1.918 / 284 | 6.658 | |

Os números de cada grupo valem para todas as falhas, não só para o recorte de
80%.

##### Candidatos a alias

37 aliases. Todos os nomes de destino foram conferidos no seed
`brazilian_cities` (lista de municípios do IBGE), na mesma UF.

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

Além desses 37, entra a exceção `piumhii` → piumhi (MG), um erro de digitação
sistemático com 183 linhas, aprovada depois do levantamento.

- **Fonte:** o nome oficial é o que está no seed (IBGE). O tipo (renomeação,
  grafia ou nome abreviado) foi classificado pelo Claude. Os atos legais de
  renomeação não foram consultados.
- **Padrão recorrente:** "do oeste" ou "doeste" no lugar de "d'Oeste"
  (`espigao do oeste`, `santa barbara doeste`, `sao jorge do oeste`,
  `alta floresta do oeste`). Não vira regra porque existem municípios
  oficiais com "do Oeste" (ex.: São Miguel do Oeste/SC); fica como alias.

##### Candidatos a regra

Padrões sistemáticos, mais baratos de tratar com uma regra do que com aliases:

- **UF colada no nome:** a sigla da própria UF no fim do nome, com espaço,
  hífen ou barra (`sao paulo - sp`, `andira-pr`, `lages - sc`,
  `cariacica / es`, `brasilia df`). Regra: remover o sufixo quando ele for
  igual à UF da linha e o resto for um município dessa UF.
- **"cidade, estado, brasil":** formato de geocodificador
  (`novo hamburgo, rio grande do sul, brasil`). Regra: usar só o primeiro
  trecho.
- **Região administrativa do DF:** o DF tem um único município, Brasília.
  Taguatinga, Ceilândia, Cruzeiro, Guará, Sobradinho, Lago Sul, Samambaia e
  as demais são regiões administrativas. Regra: em UF = DF, o município é
  Brasília. Cuidado: a regra precisa confirmar a UF pelo CEP, para não mapear
  para Brasília uma linha com a UF errada.

##### Fora do escopo dos aliases

- **Distritos e localidades** (a maior parte): `bonfim paulista` (Ribeirão
  Preto), `barra de sao joao` (Casimiro de Abreu), `arraial d ajuda` (Porto
  Seguro), `goitacazes` (Campos), `trancoso`, `maresias`, `papucaia`.
- **Erros de digitação:** 212 linhas, sendo 183 de `piumhii` (Piumhi/MG).
  Os outros têm 6 linhas ou menos (`ribeirao pretp`, `portoferreira`,
  `tabao da serra`, `sao jose do rio pret`, `alta alegre dos parecis`).
- **Cidade de outra UF:** `curitiba / SP`, `caxias do sul / SP`,
  `rio de janeiro / SP`. É inconsistência de UF, tratada pelas flags da D5.

##### Decisões tomadas

Registradas no adendo de 2026-11-08 da ADR-0002.

1. **Regras:** as três entram como a nova decisão D8. A regra do DF (R3)
   ficou como uma lista fechada das 35 regiões administrativas no seed
   `city_aliases`, em vez de uma regra que confirma a UF pelo CEP. Assim o teste
   não depende do CEP, e uma linha com a UF errada continua falhando. Com a
   lista fechada, R3 resolve 320 linhas (e não 322): ficam de fora
   `riacho fundo 2` e `ceilandia norte`, uma linha cada.
2. **`piumhii`:** entra como exceção ao critério da D2, com tipo
   `erro_digitacao_sistematico`.

##### Data dos dados

Tabelas de auditoria gravadas em 2026-11-08 às 21:30 (horário de Brasília),
pela execução com `--store-failures` da T02.

### T04. Criar o seed `city_aliases` com testes

#### O que

Criar `seeds/city_aliases.csv` com as colunas `nome_fonte`, `estado`,
`cidade_ibge` e `tipo`, mais a documentação no `schema.yml` dos seeds. O
conteúdo vem da T03: os 37 aliases, `piumhii` (exceção) e as 35 regiões
administrativas do DF com destino Brasília (R3). Testes:

- `unique_combination_of_columns` em (`nome_fonte`, `estado`);
- `not_null` nas três colunas;
- `cidade_ibge` + `estado` existem em `brazilian_cities`.

#### Aceite

`dbt seed` e `dbt test --select city_aliases` passam.

#### Evidência

_Pendente._

### T05. Integrar `city_aliases` ao teste `valid_city_for_state`

#### O que

Antes de comparar com `brazilian_cities`, o teste aplica as regras R1 (UF
colada no nome) e R2 ("cidade, estado, brasil") e resolve o nome pelo alias
(`left join` em `city_aliases`, comparando pela mesma chave `_city_key`). R1 e
R2 ficam numa macro compartilhada, que a T08 reutiliza.

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
| `stg_geolocation.geolocation_city` | 5.199 linhas / 981 pares (0,70% de 738.016) | 4.456 linhas / 963 pares (0,60%) | |
| `stg_customers.customer_city` | 2.268 linhas / 292 pares (0,72% de 314.000) | 1.918 linhas / 286 pares (0,61%) | |
| `stg_sellers.seller_city` | 290 linhas / 95 pares (3,41% de 8.500) | 284 linhas / 93 pares (3,34%) | |

Fonte e data de cada medição: ver a evidência da T01 e da T02.

## Fora do escopo

- **D7:** malha municipal do IBGE com `ST_CONTAINS`.
- `int_geolocation_by_zip` **(ADR-0001):** passa a usar a mediana da D6 e
pode ser construído sobre `int_geolocation_validated` em uma tarefa
separada.

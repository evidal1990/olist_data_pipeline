# ADR-0001: Deduplicação de geolocalização por CEP fica fora da camada staging

- **Status:** Aceita
- **Data:** 2026-10-18
- **Autora:** Edith Vidal
- **Contexto do modelo:** `models/staging/postgres_raw/stg_geolocation.sql`

## Contexto

Durante a revisão dos testes da camada staging, surgiu a pendência:

> "Nenhuma rota de deduplicação por CEP foi testada ou documentada."

Investigação:

- `stg_geolocation` já documenta (`schema.yml`) que seu grão pretendido é por
  **combinação (geolocation_lat, geolocation_lng)**, não por CEP.
- Conforme o relatório da Bronze (M2), a fonte tem **~52 registros por CEP**
  em média (1.000.163 linhas para 19.015 CEPs únicos). Ou seja, um mesmo
  `geolocation_zip_code_prefix` aparece legitimamente em múltiplas linhas,
  cada uma com uma lat/lng diferente dentro da mesma região postal.
- O projeto ainda não tem nenhum modelo nas camadas `intermediate/` ou
  `mart/` (ambas existem como diretórios, mas vazias). Nenhum model `.sql`
  referencia `stg_geolocation` hoje — apenas testes de `relationships` em
  `stg_customers`/`stg_sellers` o fazem, e esses testes verificam apenas
  *existência* do CEP, não unicidade.
- Por não haver ainda camada intermediate/mart, uma verificação de
  "existe dedup por CEP em algum lugar do pipeline" não encontra nada e a
  pendência acaba sendo registrada contra a última camada existente
  (staging) — mesmo sem ser responsabilidade dela.

## Decisão

A deduplicação para o grão **1 linha por `geolocation_zip_code_prefix`**
será implementada em um modelo da camada **intermediate**
(ex.: `int_geolocation_by_zip`), e não em `stg_geolocation`.

`stg_geolocation` mantém seu escopo atual:

- fidelidade à fonte (tipagem, nomenclatura);
- remoção apenas de duplicatas *exatas* (mesmo zip + lat + lng + city +
  state);
- carga incremental;
- documentação explícita de que o grão real não é por CEP.

## Justificativa

- **Staging é 1:1 com a fonte.** Escolher qual lat/lng "representa" um CEP
  (centróide, moda, primeiro registro, etc.) é uma decisão analítica, com
  trade-offs — não uma limpeza técnica. Isso é responsabilidade de uma
  camada que já carrega regra de negócio (intermediate/mart), não da
  staging.
- **Esconder a cardinalidade real do dado seria um antipadrão.** Se o
  dedup por CEP fosse feito em `stg_geolocation`, qualquer debug feito
  diretamente nessa tabela deixaria de refletir a granularidade real da
  fonte, dificultando investigação de qualidade de dados.
- **Reuso.** A lógica de "um ponto por CEP" provavelmente será consumida
  por mais de um modelo (ex.: enriquecimento de localização de clientes e
  de vendedores, análises de logística/geolocalização). Centralizar essa
  regra uma vez na intermediate evita duplicá-la em múltiplos marts.
- Está alinhado ao princípio de arquitetura em camadas e simplicidade
  arquitetural adotado pelo projeto.

## Consequências

- `stg_geolocation` continua, por design, com múltiplas linhas por CEP —
  isso é esperado e já documentado, não é um defeito.
- Qualquer modelo que precise de "a" localização de um CEP (1 linha por
  zip) deve consumir o futuro modelo intermediate, e não fazer join direto
  em `stg_geolocation` por `zip_code_prefix` esperando uma única linha.
- Os testes de `relationships` existentes (`stg_customers`/`stg_sellers` →
  `stg_geolocation` por `zip_code_prefix`) continuam válidos como checagem
  de existência de CEP, mas não garantem (e não devem ser interpretados
  como garantia de) unicidade de lat/lng por CEP.
- Próximo passo: implementar `models/intermediate/int_geolocation_by_zip.sql`
  com:
  - regra de deduplicação explícita e documentada (ver questão aberta
    abaixo);
  - teste de unicidade (`unique` ou `dbt_utils.unique_combination_of_columns`)
    sobre `geolocation_zip_code_prefix`.

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| Deduplicar por CEP dentro da própria `stg_geolocation` | Viola o princípio de staging 1:1 com a fonte; esconde a cardinalidade real do dado fonte. |
| Deduplicar só no mart final, sem camada intermediate | Arriscaria duplicar a mesma lógica de dedup em múltiplos marts que precisem de localização por CEP (clientes, vendedores, logística). Centralizar na intermediate evita isso. |

## Questão aberta (a resolver na implementação do `int_geolocation_by_zip`)

Qual critério usar para escolher o ponto representativo de cada CEP:

- **Centróide** (`avg(geolocation_lat)`, `avg(geolocation_lng)`) — mais
  estável estatisticamente, mas não corresponde a um ponto real no mapa.
- **Moda** (ponto mais frequente por CEP) — é um ponto real, mas pode ser
  arbitrário em CEPs com baixa frequência dominante (empate entre pontos).

A escolha e sua justificativa devem ser documentadas no `schema.yml` do
novo modelo, no mesmo nível de detalhe usado em `stg_geolocation` para
documentar seu grão.

## Adendo (2026-11-01): chave de `stg_geolocation`

Este ADR descreve o grão de `stg_geolocation` como (lat, lng), mas a regra de
remover apenas duplicatas exatas implica um grão de 5 colunas. Na tabela
anterior ao adendo, 19.562 pares (lat, lng) tinham CEP, cidade ou UF
divergentes.

**Decisão:** o `unique_key` e o teste de unicidade com `severity: error` passam
a usar `(geolocation_zip_code_prefix, geolocation_lat, geolocation_lng,
geolocation_city, geolocation_state)`. O teste em `(lat, lng)` permanece com
`severity: warn`, apenas como monitoramento de coordenadas compartilhadas.

**Consequência:** a staging passa a ter ~738 mil linhas, e o limite de
RQ-BR-02 (>= 1.000.000) passa a ser validado na source `olist_geolocation`.

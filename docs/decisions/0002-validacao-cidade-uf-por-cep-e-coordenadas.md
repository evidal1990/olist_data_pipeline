# ADR-0002: Validação de cidade/UF da geolocalização por CEP e coordenadas, sem correção linha a linha

- **Status:** Proposta
- **Data:** 2026-11-08
- **Autora:** Edith Vidal
- **Contexto do modelo:** `models/staging/postgres_raw/stg_geolocation.sql`,
`macros/valid_city_for_state.sql`, seed `brazilian_cities`
- **Relacionado:** [ADR-0001](0001-dedup-geolocalizacao-por-cep-fora-da-staging.md)

## Contexto

O teste `valid_city_for_state` em `stg_geolocation.geolocation_city`
(severidade `warn`) retornou **5.199 linhas com falha** de um total de
738.016 (**0,7%**), em **981 pares cidade/UF distintos**. O teste compara o
nome da cidade com o seed `brazilian_cities` (municípios do IBGE), ignorando
maiúsculas, acentos, apóstrofos e espaços repetidos.

Investigação na tabela de auditoria
(`postgres_staging_dbt_test__audit.valid_city_for_state_stg_geolo_dff63003e9c129c7437183a3f5f0d7f9`):

| Categoria | Linhas | Pares | Exemplos |
|---|---|---|---|
| Hífen no nome (o teste não normaliza `-`) | 743 | 18 | `mogi-guacu` (470), `biritiba-mirim`, `mogi-mirim` |
| Nome existe no IBGE, mas em outra UF | 549 | 119 | `taguatinga / DF`, `campinas / AC`, `ilha grande / RJ` |
| Caracteres corrompidos | 12 | 11 | `maceia³` |
| Não é município do IBGE | 3.895 | 833 | distritos (`ceilandia`, `trancoso`, `abrantes`), grafia antiga (`embu`, `parati`, `santana do livramento`, `acu`), erros de digitação (`piumhii`) |

Na categoria "outra UF", o nome isolado não diz qual campo está errado. Por
isso cruzamos os outros sinais disponíveis na própria linha:

- **Faixa oficial de CEP por UF:** o CEP concorda com a UF declarada em
**540 de 549** linhas. A UF quase nunca é o campo errado.
- **Coordenada contra a mediana das coordenadas do mesmo CEP** (em todo o
`stg_geolocation`):
  - **434 linhas** (108 pares) ficam a menos de 50 km da mediana do CEP. CEP,
  UF e coordenada concordam. O nome é de um distrito ou localidade que tem
  um município homônimo em outro estado (ex.: Taguatinga é região
  administrativa do DF e município do TO).
  - **115 linhas** (29 pares) ficam a 50 km ou mais. A coordenada está
  errada: o geocodificador da fonte resolveu o nome para o homônimo de
  outro estado (ex.: `campinas / AC` com coordenadas de Campinas/SP).
- Em toda a tabela, apenas **33 linhas** têm coordenadas fora da caixa
delimitadora do Brasil.

A fonte (dataset público do Olist) é estática e não está sob nosso controle.

## Decisões

### D1. Corrigir a chave de comparação de cidade para tratar hífen como espaço

`_city_key` (em `macros/valid_city_for_state.sql`) passa a substituir `-` por
espaço, como já faz com o apóstrofo. É uma falha da chave de comparação, não
um problema do dado.

### D2. Criar o seed `city_aliases` para renomeações e grafias oficiais divergentes

Mapeamento `nome_fonte, estado → nome_ibge` (ex.: `embu, SP → Embu das Artes`;
`parati, RJ → Paraty`; `santana do livramento, RS → Sant'Ana do Livramento`;
`acu, RN → Assú`). Ele é usado pelo teste `valid_city_for_state` e pelo modelo
intermediate da D5.

**Critério de inclusão:** só entram nomes que correspondem a um município
real com outro nome oficial (renomeação ou variação ortográfica). Distritos,
erros de digitação e casos isolados **não** entram.

### D3. Não corrigir linha a linha distritos, erros de digitação e UF divergente

Não criamos uma lista manual de correções por registro. Motivos:

- **Custo contra volume:** cerca de 950 pares e ~0,6% das linhas, numa cauda
longa de poucas ocorrências por par.
- **Muitos casos não são erros.** Distrito é endereço legítimo; trocá-lo pelo
município perde informação.
- **A fonte é estática e externa.** Uma correção manual vira uma regra
invisível, que diverge da origem e não cobre novas cargas.
- **Governança:** uma lista por linha não tem dono natural, não escala e é
difícil de auditar.

O teste continua em `warn` na staging, como monitoramento. Quando uma correção
for necessária, ela será **por regra** (D4 a D6).

### D4. Hierarquia de confiança dos sinais de localização

**CEP > UF > coordenada > nome da cidade.**

- A faixa de CEP determina a UF com segurança e é o sinal mais confiável.
- A coordenada só é considerada válida quando concorda com o CEP.
- O nome da cidade é o sinal menos confiável (texto livre, distritos,
homônimos).

### D5. Criar `int_geolocation_validated` com flags de qualidade explicáveis

Novo modelo na camada intermediate, no mesmo grão de `stg_geolocation`. A
staging continua 1:1 com a fonte, conforme a ADR-0001.

| Coluna | Regra |
|---|---|
| `uf_from_cep` | Faixa oficial de CEP por UF (novo seed `cep_uf_ranges`) |
| `is_uf_consistent` | `uf_from_cep = geolocation_state` |
| `is_coord_in_brazil` | Coordenada dentro da caixa delimitadora do Brasil |
| `coord_distance_km_to_cep_median` | Distância até a mediana das coordenadas do CEP |
| `is_coord_outlier` | Distância acima do limite configurado (`var`) ou coordenada fora do Brasil |
| `city_ibge` | Nome oficial após aplicar `city_aliases`, quando houver correspondência |
| `is_city_ibge_municipality` | Nome (após aliases) é um município do IBGE na UF |
| `geo_quality_status` | `ok`, `distrito_ou_localidade`, `coord_suspeita` ou `uf_divergente` |

O limite de distância fica em uma variável do dbt
(`geo_coord_outlier_km`), com valor inicial de **50 km**.

### D6. Ponto de referência do CEP = mediana das coordenadas

O ponto que representa um CEP é a **mediana** de lat e lng das linhas desse
CEP. Ele é usado para:

- calcular `coord_distance_km_to_cep_median` (D5);
- substituir a coordenada quando `is_coord_outlier = true`, nos modelos que
consomem localização;
- servir de critério do futuro `int_geolocation_by_zip`.

Isso **resolve a questão aberta da ADR-0001** (centróide ou moda): a média
(centróide) é sensível aos outliers encontrados aqui, como coordenadas na
Itália e homônimos de outros estados. A moda é arbitrária em CEPs sem ponto
dominante. A mediana é robusta a outliers.

## Consequências

- A taxa de falha do `valid_city_for_state` cai depois da D1 e da D2, ficando
restrita a ruído conhecido da fonte. A correção do hífen também afeta os
testes do mesmo tipo em `customer_city` e `seller_city`, que usam a mesma
macro.
- Os modelos que precisam de cidade/UF confiáveis (KPIs de geolocalização e
logística) devem consumir `int_geolocation_validated` e filtrar ou agrupar
por `geo_quality_status`, em vez de ler o nome direto de `stg_geolocation`.
- Os distritos permanecem como estão. KPIs por município mostrarão
"não identificado" para eles até a evolução da D7.
- Novos artefatos para manter: os seeds `cep_uf_ranges` (estável, muda
raramente) e `city_aliases` (cresce apenas pelo critério da D2).
- O prefixo de CEP de 5 dígitos determina a UF, mas **não** o município: um
prefixo pode abranger mais de uma cidade. O CEP sozinho não substitui o
nome da cidade.

## Alternativas consideradas

| Alternativa | Por que foi rejeitada |
|---|---|
| Correção manual linha a linha | Custo alto para ~0,6% das linhas, ambígua para distritos e UF divergente, difícil de auditar e manter (D3). |
| Usar apenas as coordenadas para decidir cidade/UF | 115 das 549 linhas com UF divergente têm a coordenada errada. Sem cruzar com o CEP, a coordenada propagaria o erro do geocodificador. |
| Corrigir na própria staging | Viola o princípio de staging 1:1 com a fonte (ADR-0001). |
| Elevar o teste para `error` | Bloquearia o pipeline por ruído conhecido de uma fonte que não controlamos. |
| Malha municipal do IBGE com `ST_CONTAINS` agora | Resolveria distrito → município, mas exige ingerir e manter shapefiles. Fica adiada (D7). |

## D7. Evolução futura (fora do escopo desta ADR)

Carregar a malha municipal do IBGE como `GEOGRAPHY` no BigQuery e derivar o
município com `ST_CONTAINS`, **apenas para coordenadas não marcadas como
outlier**. Isso transformaria `distrito_ou_localidade` em município de
verdade. Deve ser feito quando algum KPI precisar de granularidade municipal.

## Questões abertas

- **Limite de outlier:** 50 km é um ponto de partida. Calibrar olhando a
distribuição de `coord_distance_km_to_cep_median`, já que CEPs rurais
cobrem áreas maiores.
- **Limiar percentual do teste:** `warn_if`/`error_if` do dbt comparam
contagem absoluta, não percentual. Avaliar um parâmetro de taxa máxima no
teste customizado, ou acompanhar a taxa (falhas / total) no dashboard da
staging.

## Plano de implementação

1. D1: corrigir `_city_key` e rodar os testes de `customer_city`,

   `seller_city` e `geolocation_city`.
2. D2: criar o seed `city_aliases` e integrá-lo ao teste.
3. D5: criar o seed `cep_uf_ranges` e o modelo `int_geolocation_validated`,

   com testes (`accepted_values` em `geo_quality_status`, `not_null` em
    `uf_from_cep`, `expression_is_true` para `is_uf_consistent` com
    severidade `warn`).
4. Rodar `dbt build` e atualizar os dashboards da staging.
5. Mudar o status desta ADR para **Aceita** após a revisão.

## Adendo (2026-11-08): regras de normalização e exceção de alias

O levantamento da T03 (ver
[backlog](0002-backlog.md#t03-levantar-os-candidatos-a-alias)) encontrou
padrões sistemáticos que não são renomeações e por isso não cabem no critério
da D2. Também encontrou um erro de digitação com volume alto.

### D8. Regras de normalização do nome da cidade

Antes de comparar com o seed, o teste `valid_city_for_state` e o
`int_geolocation_validated` (D5) aplicam:

- **R1. UF colada no nome:** se o nome termina com a sigla da própria UF da
  linha, separada por espaço, hífen ou barra (`sao paulo - sp`, `andira-pr`,
  `cariacica / es`), o sufixo é removido. Só vale quando a sigla é igual à UF
  da linha. Efeito medido: 36 linhas.
- **R2. "cidade, estado, brasil":** formato de geocodificador
  (`novo hamburgo, rio grande do sul, brasil`). Usa-se só o trecho antes da
  primeira vírgula. Efeito medido: 11 linhas.
- **R3. Regiões administrativas do DF:** o DF tem um único município,
  Brasília. As 35 regiões administrativas oficiais (Taguatinga, Ceilândia,
  Guará, Sobradinho, Lago Sul etc.) entram no seed `city_aliases` com destino
  Brasília e tipo `regiao_administrativa_df`. Efeito medido: 320 linhas.

R3 usa uma lista fechada no seed, e não uma regra do tipo "toda cidade com
UF = DF é Brasília". Assim o teste não depende do CEP, e uma linha com a UF
errada (ex.: `goiania / DF`) continua falhando.

### D2 (revisão). Exceção para erro de digitação sistemático

`piumhii` → Piumhi/MG entra no `city_aliases` como exceção ao critério da D2,
com tipo `erro_digitacao_sistematico`. Motivo: é o único erro de digitação com
volume relevante (183 linhas em geolocalização e clientes), e a grafia correta
não é ambígua. Os demais erros de digitação encontrados têm 6 linhas ou menos
e continuam fora.

Novas exceções só entram com a mesma justificativa: erro sistemático, volume
relevante e correção sem ambiguidade, registrados neste adendo.

### Consequências

- O seed `city_aliases` ganha a coluna `tipo` (`renomeacao`, `grafia_oficial`,
  `nome_abreviado`, `regiao_administrativa_df`, `erro_digitacao_sistematico`),
  para que cada linha seja auditável.
- Efeito esperado sobre as 6.658 falhas depois da T02: aliases 1.744 linhas
  (incluindo `piumhii`), R1 36, R2 11, R3 320. Sobram cerca de 4.547 linhas
  (distritos, localidades, erros de digitação pequenos e UF errada),
  monitoradas pela D3.
- R1 e R2 são implementadas no teste (T05) e repetidas no
  `int_geolocation_validated` (T08). Para não duplicar a lógica, ela deve
  ficar numa macro compartilhada.

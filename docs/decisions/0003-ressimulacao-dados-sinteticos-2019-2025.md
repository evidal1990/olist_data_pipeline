# ADR-0003: Ressimulação dos dados sintéticos de 2019 a 2025

- **Status:** Aceita
- **Data:** 2026-11-19
- **Autora:** Edith Vidal
- **Código:** `scripts/data_simulation/` (`resimulate_olist.py`, `config.py`, `comments.py`)

## Contexto

A base do schema `orders` combina os ~99 mil pedidos do Olist público
(set/2016 a ago/2018) com pedidos sintéticos que estendem a série até 2025.
O perfil de negócio da staging (`docs/data-quality/profile/retrato_negocio_staging.md`,
seção 2) apontou que a parte sintética não parecia real:

- o frete não dependia da distância (RJ→AM custava o mesmo que RJ→SP);
- as distribuições eram uniformes demais, sem concentração de vendedores
  nem sazonalidade;
- havia muitas parcelas vazias ou zeradas, inclusive em boleto e débito;
- alguns campos tinham sinais de perda de dado em massa.

Uma base assim produz KPIs sem sentido (frete médio por região, prazo de
entrega, concentração de receita) e esconde os problemas de qualidade que os
testes deveriam capturar.

## Decisão

Regerar toda a parte sintética com um simulador baseado em regras de
negócio, preservando intactos os pedidos originais do Olist.

### O que é preservado

- Pedidos anteriores a 2018-09-01: datas e status do Olist original.
- IDs: 350.580 `order_id` existentes são reaproveitados com conteúdo novo;
  598.420 são novos.
- Os CSVs de `olist_geolocation` (não mudam).
- Os nomes, os tipos e a ordem das colunas das 7 tabelas.

### Regras de negócio simuladas

Todos os parâmetros ficam em `config.py`, para que ajustes não exijam ler o
gerador. A semente fixa (`SEED = 20261118`) torna a geração reprodutível.

| Tema | Regra |
|---|---|
| Volume | Pedidos por ano (26 mil em set–dez/2018 até 160 mil em 2025), salto em 2020, sazonalidade mensal (Black Friday ×1,4) e por dia da semana |
| Frete | Função da distância rodoviária estimada, do peso e da região de destino (Norte ×1,35, Nordeste ×1,15), corrigida pela inflação |
| Prazo | Trânsito proporcional à distância e à região, com choques logísticos (pandemia, greve dos Correios 2020, enchentes no RS em 2024, fins de ano) |
| Concentração | Popularidade de vendedores e produtos log-normal; os 10% maiores vendedores ficam com ~85% da receita |
| Clientes | Recompra baixa (3% a 5%); preferência por vendedor da mesma UF/região; crescimento mais rápido fora do Sudeste |
| Pagamento | Mix por ano (crédito sobe, boleto cai); boleto, débito e voucher sempre em 1x; parcelas do cartão por faixa de valor (parcela mínima de R$ 15) |
| Avaliação | Nota consequência do atraso e da categoria; comentários em português |

### Parcelas: opção B

Corrigir quase todas as parcelas inválidas, mas manter um resíduo realista
de **20 linhas de cartão** (12 com parcela 0 e 8 vazias, ~2 a cada 100 mil),
na mesma ordem de grandeza do Olist original. O teste
`payment_installments >= 1` deve falhar exatamente nessas 20 linhas.

Alternativas descartadas:

- **A, corrigir tudo:** a base fica limpa demais, e o teste nunca falha.
  Não exercita a regra de qualidade.
- **C, manter como estava:** milhares de linhas inválidas, inclusive em
  boleto, que distorcem o KPI de parcelamento médio.

### Sujeira plantada com gabarito

Problemas raros são plantados de propósito, e cada caso é registrado em
`_gabarito/planted_issues.csv` (tabela, chave, problema, coluna, valor
plantado). Isso permite medir se os testes capturam o que deveriam.

| Tabela | Problema | Casos |
|---|---|---|
| orders | coleta antes da aprovação | 4.666 |
| orders | entregue sem data de entrega | 93 |
| orders | cancelado com data de entrega | 104 |
| order_payments | pagamento difere dos itens por centavos | 10.484 |
| order_payments | voucher excedente | 1.048 |
| order_payments | parcela 0 / vazia | 12 / 8 |
| order_reviews | avaliação duplicada no mesmo pedido | 2.068 |
| products | peso zero | 56 |
| customers e sellers | cidade com grafia variante ou inválida, CEP sem geolocalização | ~9 mil |

No banco, as contagens de cada problema são o gabarito mais os casos que já
existiam no Olist original (ex.: coleta antes da aprovação = 4.666 + 1.359).

## Carga e sincronização

1. **PostgreSQL (2026-11-19):** backup antes da carga em
   `~/Downloads/backup_postgres/production_orders_antes_ressimulacao_20261119.dump`
   (`pg_dump -Fc`, schema `orders`). Em seguida, `TRUNCATE` + `COPY` das 7
   tabelas numa única transação, com lista explícita de colunas para que
   `updated_at` receba `now()`, seguidos de `ANALYZE`. `olist_geolocation`
   não foi recarregada.
2. **Airbyte → BigQuery:** como os `order_id` antigos foram reaproveitados
   com outro conteúdo, um sync incremental com deduplicação deixaria itens,
   pagamentos e avaliações antigos órfãos em `postgres_raw`. Por isso, os 7
   streams foram sincronizados uma vez em **Full Refresh | Overwrite**.
   `olist_geolocation` ficou fora do sync. A conexão passou de cron diário
   para agendamento manual, para não repetir o Full Refresh todo dia.
   O primeiro sync falhou porque o IP da máquina na rede local mudou por
   DHCP (`192.168.68.50` → `192.168.68.52`) e a fonte Postgres apontava
   para o IP antigo. O host foi atualizado para o IP novo; isso pode
   voltar a acontecer, e `host.docker.internal` é a alternativa estável.

## Consequências

- Os KPIs passam a ter forma realista. Volume total: 1,05 milhão de pedidos
  e 1,27 milhão de itens.
- Os números dos dashboards de qualidade da staging mudam bastante; não
  são comparáveis com as execuções anteriores a 2026-11-19.
- O gabarito vira a referência para avaliar a cobertura dos testes dbt.
- A geração leva ~8 min. A etapa de sujeira plantada responde por ~6,5 min
  e ainda não foi otimizada.

## Riscos

- O reaproveitamento de IDs quebra qualquer sync incremental feito sem
  reset. Toda recarga futura da base deve repetir o Full Refresh.
- O conteúdo do gabarito depende da semente. Mudar `config.py` exige
  regerar e recarregar a base e o gabarito juntos.

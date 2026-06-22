# Indicadores de Clientes

## Objetivo

Monitorar o crescimento, retenção, rentabilidade e comportamento dos clientes por meio de métricas acionáveis, comparativas e orientadas à tomada de decisão.

---

# 1. Crescimento de Clientes Ativos (%)

## Objetivo

Aumentar a base de clientes ativos do negócio.

## Pergunta de negócio

> Nossa base de clientes ativos está crescendo ou diminuindo?

## Dados necessários

* customer_id
* order_id
* order_purchase_timestamp

## Definição

Cliente ativo é um cliente que realizou pelo menos uma compra no período.

## Fórmula

```text
((Clientes Ativos Atual - Clientes Ativos Anterior)
/
Clientes Ativos Anterior)
× 100
```

## Benchmark

| Nível        | Meta     |
| ------------ | -------- |
| 🟢 Excelente | > 15%    |
| 🟡 Bom       | 5% a 15% |
| 🟠 Atenção   | 0% a 5%  |
| 🔴 Crítico   | < 0%     |

## Responsáveis

* Marketing
* CRM
* Growth

## Contrapesos

* CAC
* Receita por Cliente

## Pergunta estratégica

> Estamos adquirindo clientes rentáveis?

---

# 2. Taxa de Recompra (%)

## Objetivo

Aumentar a retenção e a fidelização dos clientes.

## Pergunta de negócio

> Quantos clientes retornam para realizar novas compras?

## Dados necessários

* customer_unique_id
* order_id

## Fórmula

```text
(Clientes com mais de um pedido
/
Clientes Totais)
× 100
```

## Benchmark

| Nível        | Meta      |
| ------------ | --------- |
| 🟢 Excelente | > 40%     |
| 🟡 Bom       | 30% a 40% |
| 🟠 Atenção   | 20% a 30% |
| 🔴 Crítico   | < 20%     |

## Responsáveis

* CRM
* Marketing de Relacionamento
* Customer Success

## Contrapesos

* Margem
* Receita

## Pergunta estratégica

> Estamos fidelizando sem sacrificar a rentabilidade?

---

# 3. Frequência Média de Compra

## Objetivo

Aumentar o número de compras realizadas por cliente.

## Pergunta de negócio

> Com que frequência os clientes compram?

## Dados necessários

* customer_unique_id
* order_id

## Fórmula

```text
Total de Pedidos
/
Clientes Ativos
```

Resultado:

> Número médio de compras por cliente.

## Comparações recomendadas

* Histórico
* Categoria
* Segmento de cliente

## Responsáveis

* CRM
* Comercial
* Marketing

## Contrapesos

* Satisfação
* Churn

## Pergunta estratégica

> O aumento da frequência mantém uma boa experiência?

---

# 4. LTV (Lifetime Value)

## Objetivo

Maximizar o valor gerado por cada cliente ao longo do relacionamento.

## Pergunta de negócio

> Quanto cada cliente gera de receita durante sua vida útil?

## Dados necessários

* customer_unique_id
* payment_value
* order_id

## Fórmula simplificada

```text
Ticket Médio
×
Frequência Média de Compra
```

## Fórmula completa

```text
Receita Total
/
Clientes Totais
```

## Comparações recomendadas

* Segmentos
* Categorias
* Períodos

## Meta

> O LTV deve crescer ao longo do tempo.

## Responsáveis

* CRM
* Marketing
* Diretoria Comercial

## Contrapesos

* CAC

## Pergunta estratégica

> O valor gerado cobre o custo de aquisição?

---

# 5. LTV/CAC (Índice)

## Objetivo

Avaliar a rentabilidade da aquisição de clientes.

## Pergunta de negócio

> O valor gerado pelo cliente compensa o custo de aquisição?

## Dados necessários

* LTV
* Investimento em Marketing
* Novos Clientes

## Fórmulas

### LTV/CAC

```text
LTV
/
CAC
```

### CAC

```text
Investimento em Marketing
/
Novos Clientes
```

## Benchmark

| Nível        | Meta  |
| ------------ | ----- |
| 🟢 Excelente | > 5   |
| 🟡 Bom       | 3 a 5 |
| 🟠 Atenção   | 1 a 3 |
| 🔴 Crítico   | < 1   |

## Responsáveis

* Marketing
* Growth
* Financeiro

## Contrapesos

* Crescimento

## Pergunta estratégica

> Estamos crescendo de forma sustentável?

---

# 6. Segmentação RFM (Complementar)

## Objetivo

Segmentar clientes por comportamento para priorizar ações e investimentos.

## Pergunta de negócio

> Quais clientes possuem maior valor para o negócio?

## Dados necessários

* customer_unique_id
* order_purchase_timestamp
* payment_value
* order_id

## Definições

### R - Recência

Dias desde a última compra.

### F - Frequência

Quantidade de compras.

### M - Monetário

Valor total gasto.

## Ranking interno sugerido

### Campeões

* Alto R
* Alto F
* Alto M

### Fiéis

* Médio R
* Alto F
* Médio M

### Em risco

* Baixo R
* Médio F
* Baixo ou Médio M

### Perdidos

* Baixo R
* Baixo F
* Baixo M

## Responsáveis

* CRM
* Marketing
* Customer Success

## Contrapesos

* Investimento em ações

## Pergunta estratégica

> Estamos investindo nos clientes que realmente geram valor?

---

# Princípios de Utilização dos Indicadores

Todos os indicadores devem:

* Ser comparáveis entre períodos e segmentos.
* Ser simples de interpretar.
* Orientar decisões e ações concretas.
* Utilizar taxas e proporções em vez de apenas volumes.
* Possuir fórmulas auditáveis.
* Incentivar mudanças de comportamento e melhoria contínua.

---

# Escala de Desempenho

🟢 Excelente → desempenho acima do esperado

🟡 Bom → desempenho satisfatório

🟠 Atenção → necessita monitoramento

🔴 Crítico → exige ação imediata

---

# Foco do Lean Analytics

> A melhor métrica é aquela que leva uma pessoa a tomar uma decisão diferente amanhã.

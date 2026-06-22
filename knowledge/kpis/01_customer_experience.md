# Indicadores de Customer Experience (CX)

## Objetivo

Monitorar a experiência dos clientes por meio de métricas acionáveis, comparativas e orientadas à tomada de decisão, garantindo a melhoria contínua da operação sem comprometer a rentabilidade do negócio.

---

# 1. NPS Aproximado

## Objetivo

Medir o nível geral de satisfação e lealdade dos clientes.

## Pergunta de negócio

> Os clientes recomendariam a empresa para outras pessoas?

## Dados necessários

* review_score
* order_id
* customer_id

## Classificação

* Promotores = nota 5
* Neutros = nota 4
* Detratores = nota 1, 2 ou 3

## Fórmula

```text
(% Promotores) - (% Detratores)
```

## Benchmark

| Nível        | Meta    |
| ------------ | ------- |
| 🟢 Excelente | > 50    |
| 🟡 Bom       | 30 a 50 |
| 🟠 Atenção   | 0 a 30  |
| 🔴 Crítico   | < 0     |

## Responsáveis

* Customer Experience
* Customer Success
* Diretoria de Operações

## Contrapesos

* Receita
* Crescimento

## Pergunta estratégica

> Estamos aumentando a satisfação sem comprometer a rentabilidade?

---

# 2. Percentual de Avaliações 5 Estrelas

## Objetivo

Aumentar a proporção de experiências excepcionais.

## Pergunta de negócio

> Quantos clientes tiveram uma experiência excelente?

## Dados necessários

* review_score

## Fórmula

```text
(Reviews 5 estrelas / Total de Reviews) × 100
```

## Benchmark

| Nível        | Meta      |
| ------------ | --------- |
| 🟢 Excelente | > 80%     |
| 🟡 Bom       | 70% a 80% |
| 🟠 Atenção   | 60% a 70% |
| 🔴 Crítico   | < 60%     |

## Responsáveis

* Customer Experience
* Operações
* Logística

## Contrapesos

* Volume de pedidos

## Pergunta estratégica

> Conseguimos manter a satisfação mesmo com o crescimento da operação?

---

# 3. Percentual de Avaliações Negativas (1 e 2 Estrelas)

## Objetivo

Identificar rapidamente problemas operacionais e de atendimento.

## Pergunta de negócio

> Qual percentual dos clientes teve uma experiência ruim?

## Dados necessários

* review_score

## Fórmula

```text
(Reviews nota 1 ou 2 / Total de Reviews) × 100
```

## Benchmark

| Nível        | Meta     |
| ------------ | -------- |
| 🟢 Excelente | < 2%     |
| 🟡 Bom       | 2% a 5%  |
| 🟠 Atenção   | 5% a 10% |
| 🔴 Crítico   | > 10%    |

## Responsáveis

* Customer Experience
* Qualidade
* Operações

## Contrapesos

* Receita

## Pergunta estratégica

> Existem categorias lucrativas que estão gerando insatisfação?

---

# 4. Avaliação por Categoria

## Objetivo

Identificar categorias de produtos que impactam a experiência do cliente.

## Pergunta de negócio

> Quais categorias possuem melhor ou pior percepção dos clientes?

## Dados necessários

* product_category_name
* product_id
* review_score

## Fórmula

```text
AVG(review_score)
por categoria
```

## Comparações recomendadas

* Categoria
* Período
* Região

## Responsáveis

* Gestão de Produtos
* Marketplace
* Customer Experience

## Contrapesos

* Receita da categoria

## Pergunta estratégica

> Categorias mais rentáveis também são as mais bem avaliadas?

---

# 5. Avaliação por Estado

## Objetivo

Identificar problemas regionais que afetam a experiência dos clientes.

## Pergunta de negócio

> Existem estados com níveis de satisfação inferiores à média?

## Dados necessários

* customer_state
* review_score

## Fórmula

```text
AVG(review_score)
por estado
```

## Comparações recomendadas

* Estado
* Região
* Evolução histórica

## Responsáveis

* Logística
* Customer Experience
* Supply Chain

## Contrapesos

* Lead Time
* OTD (On-Time Delivery)

## Pergunta estratégica

> Estados com baixa satisfação também apresentam atrasos de entrega?

---

# 6. Tempo Médio de Resposta às Avaliações

## Objetivo

Melhorar a velocidade de resposta ao cliente.

## Pergunta de negócio

> Quanto tempo a empresa leva para responder uma avaliação?

## Dados necessários

* review_creation_date
* review_answer_timestamp

## Fórmula

```text
AVG(
review_answer_timestamp
-
review_creation_date
)
```

Unidade: horas.

## Benchmark

| Nível        | Meta          |
| ------------ | ------------- |
| 🟢 Excelente | < 24 horas    |
| 🟡 Bom       | 24 a 48 horas |
| 🟠 Atenção   | 2 a 5 dias    |
| 🔴 Crítico   | > 5 dias      |

## Responsáveis

* SAC
* Customer Success
* Customer Experience

## Contrapesos

* Qualidade da resposta

## Pergunta estratégica

> Estamos respondendo rápido ou resolvendo o problema?

---

# Princípios de Utilização dos Indicadores

Todos os indicadores devem:

* Ser comparáveis entre períodos, segmentos e regiões.
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

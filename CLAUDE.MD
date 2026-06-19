# CLAUDE.md

# Supply Chain Analytics Platform

## Visão geral

Este projeto simula uma plataforma moderna de dados utilizada por uma empresa fictícia de Supply Chain.

O objetivo é construir uma arquitetura ponta a ponta para ingestão, armazenamento e posterior transformação dos dados.

Este repositório deve seguir padrões próximos aos utilizados em ambientes corporativos reais.

---

## Contexto do negócio

A empresa atua na gestão da cadeia de suprimentos e precisa consolidar dados operacionais para posterior análise.

As principais entidades do negócio são:

* clientes
* pedidos
* produtos
* fornecedores
* pagamentos de pedidos
* avaliações de pedidos
* items do pedido
* geolocalização

Os dados são armazenados em um banco PostgreSQL transacional e precisam ser enviados para o BigQuery.

---

## Papel do Claude

Atue como um Engenheiro de Dados e Analytics Engineer Sênior.

Ao gerar soluções:

* priorize simplicidade
* priorize modularidade
* priorize escalabilidade
* priorize observabilidade
* priorize manutenibilidade
* explique decisões arquiteturais
* explique trade-offs quando houver múltiplas abordagens

Evite soluções excessivamente complexas.

Pense como um profissional construindo uma plataforma de dados real.

---

## Escopo atual do projeto

O projeto é responsável por:

* configurar o ambiente Docker
* configurar o PostgreSQL
* configurar o Airbyte
* configurar o BigQuery
* realizar a ingestão dos dados
* documentar a arquitetura

Neste momento, o projeto não contempla:

* APIs REST
* Machine Learning
* dashboards
* modelagem dimensional
* transformações de negócio

---

## Arquitetura atual

PostgreSQL (Docker Container)

↓

Airbyte (Docker Container)

↓

BigQuery (raw)

---

## Evolução futura da plataforma

Estas etapas não fazem parte do escopo atual.

BigQuery (raw)

↓

dbt

↓

Databricks

↓

Power BI

Não implementar essas etapas neste repositório.

---

## Infraestrutura local

O ambiente é totalmente containerizado utilizando Docker.

Containers previstos:

* PostgreSQL
* Airbyte

O Airbyte será responsável pela ingestão.

Não desenvolver um serviço próprio de ingestão em Python.

Priorizar a utilização dos conectores nativos do Airbyte.

---

## Stack tecnológica

Banco transacional:

* PostgreSQL

Ferramenta de ingestão:

* Airbyte

Data Warehouse:

* BigQuery

Containerização:

* Docker

Versionamento:

* Git

IDE:

* Cursor

Assistente:

* Claude Code

---

## Regras para o Airbyte

Utilizar o Airbyte como ferramenta principal de ingestão.

Priorizar:

* conectores oficiais
* sincronização incremental quando disponível
* sincronização full refresh apenas quando necessário
* configurações reproduzíveis
* configurações versionáveis

Sempre sugerir a melhor estratégia entre:

* Full Refresh
* Incremental Append
* Incremental Append + Deduped

Explicar os trade-offs de cada abordagem.

---

## PostgreSQL

PostgreSQL é a fonte da verdade.

Nunca modificar tabelas de origem.

Sempre utilizar consultas explícitas.

Priorizar tabelas que possuam:

* updated_at
* created_at
* id incremental

---

## BigQuery

Objetivo:

Armazenar dados brutos (raw).

Boas práticas:

* utilizar particionamento quando aplicável
* utilizar clustering quando aplicável
* minimizar custo de processamento
* evitar tabelas desnecessariamente grandes

Não implementar transformações de negócio nesta etapa.

---

## Observabilidade

Sempre considerar:

* logs de sincronização
* status das execuções
* tempo de execução
* quantidade de registros processados
* erros encontrados

---

## Como o Claude deve responder

Ao gerar soluções:

* priorizar simplicidade
* explicar as decisões tomadas
* sugerir melhorias de performance
* sugerir melhorias de observabilidade
* sugerir melhorias de escalabilidade

Não assumir implementações que ainda não existem.

Não criar um serviço próprio de ingestão em Python.

Sempre respeitar as convenções definidas neste documento.
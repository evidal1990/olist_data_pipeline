# Olist Data Pipeline

Plataforma analítica ponta a ponta para o dataset da Olist: ingestão via Airbyte (PostgreSQL → BigQuery) e transformações analíticas com dbt.

## Estrutura do Projeto

```
olist_data_pipeline/
├── .claude/                    # Configurações e base de conhecimento do Claude Code
├── analyses/                   # Análises ad-hoc em dbt
├── docs/                       # Documentação técnica e funcional
├── logs/                       # Logs de execução do dbt
├── macros/                     # Macros reutilizáveis do dbt
├── models/                     # Modelos dbt (camadas analíticas)
│   └── staging/
│       └── postgres_raw/
│           ├── _postgres_raw__sources.yml
│           └── stg_orders.sql
├── seeds/                      # Seeds (dados estáticos) do dbt
├── snapshots/                  # Snapshots (SCD) do dbt
├── tests/                      # Testes customizados do dbt
└── README.md
```

> Observação: `.venv/` e `.dbt/` foram ocultas por completo; arquivos `.gitkeep` e o conteúdo de `docs/` também foram ocultos. Também foram omitidos arquivos de configuração (`.env`, `.gitignore`, `Dockerfile`, `dbt_project.yml`, `requirements.txt`), credenciais (`airbyte-bq-key.json`, `dbt-bq-user-key.json`), `.git/`, `target/` (artefatos gerados pelo dbt) e `.DS_Store`.

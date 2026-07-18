# Usando uma imagem base com Python
FROM python:3.11-slim

# Definindo o mantenedor
LABEL maintainer="Olist Team"

# Atualizando a lista de pacotes e instalando dependências
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    vim \
    nano \
    google-cloud-sdk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Criando um diretório de trabalho
WORKDIR /olist

# Instalando DBT e adaptador para o bigquery
RUN pip install dbt-core==1.12.0
RUN pip install dbt-bigquery==1.12.0

# Definir o comando padrão para execução quando o container for iniciado
CMD ["/bin/bash"]

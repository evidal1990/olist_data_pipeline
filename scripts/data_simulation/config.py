"""Parâmetros da ressimulação dos dados Olist (ADR-0003).

Tudo que muda o "comportamento de negócio" simulado fica aqui, para que um
ajuste não exija ler o gerador inteiro.
"""
import pandas as pd

SEED = 20261118
DATA_CUTOFF = pd.Timestamp("2025-12-31 23:59:59")
# Pedidos com hora e anteriores a esta data são do Olist público: datas e status preservados.
ORIGINAL_END = pd.Timestamp("2018-09-01")
SYNTH_START = pd.Timestamp("2018-09-01")

# Pedidos por ano no período simulado (2018 = set–dez). Total ~890 mil + ~99 mil originais.
YEARLY_ORDERS = {
    2018: 26_000,
    2019: 85_000,
    2020: 125_000,   # salto da pandemia a partir de abril
    2021: 135_000,
    2022: 128_000,   # ressaca pós-pandemia
    2023: 140_000,
    2024: 150_000,
    2025: 160_000,
}

MONTH_FACTOR = {1: 0.95, 2: 0.85, 3: 1.00, 4: 0.95, 5: 1.05, 6: 0.95,
                7: 0.95, 8: 1.00, 9: 0.95, 10: 1.00, 11: 1.40, 12: 1.10}
WEEKDAY_FACTOR = {0: 1.12, 1: 1.10, 2: 1.05, 3: 1.00, 4: 0.94, 5: 0.80, 6: 0.88}  # seg..dom

REGION = {
    "AC": "N", "AM": "N", "AP": "N", "PA": "N", "RO": "N", "RR": "N", "TO": "N",
    "AL": "NE", "BA": "NE", "CE": "NE", "MA": "NE", "PB": "NE", "PE": "NE", "PI": "NE", "RN": "NE", "SE": "NE",
    "DF": "CO", "GO": "CO", "MS": "CO", "MT": "CO",
    "ES": "SE", "MG": "SE", "RJ": "SE", "SP": "SE",
    "PR": "S", "RS": "S", "SC": "S",
}
# Peso extra por ano (a partir de 2018) na escolha da UF de novos clientes:
# o e-commerce cresce mais rápido fora do Sudeste.
REGION_CUSTOMER_DRIFT = {"N": 0.07, "NE": 0.06, "CO": 0.03, "S": 0.01, "SE": -0.015}

# Preferência do cliente por vendedor próximo (multiplica o peso do produto).
AFFINITY_SAME_STATE = 3.2
AFFINITY_SAME_REGION = 1.6

# Frete por item: (base + km*a + kg*(b + km*c)) * fator remoto * inflação * ruído
FREIGHT = dict(base=7.5, per_km=0.0055, per_kg=1.6, per_kg_km=0.0011, road_factor=1.3,
               noise_sigma=0.13, combined_item_factor=0.5, free_shipping_rate=0.002)
FREIGHT_REMOTE = {"N": 1.35, "NE": 1.15, "CO": 1.08, "SE": 1.0, "S": 1.0}

# Prazo de trânsito (dias) = (1.5 + km/380) * fator região * picos * ruído log-normal
TRANSIT_REGION = {"N": 1.5, "NE": 1.2, "CO": 1.1, "SE": 1.0, "S": 1.0}
# Períodos de estresse logístico: (início, fim, multiplicador do trânsito)
LOGISTIC_SHOCKS = [
    ("2020-03-20", "2020-06-30", 1.30),  # início da pandemia
    ("2020-08-17", "2020-09-22", 1.35),  # greve dos Correios 2020
    ("2021-11-20", "2021-12-24", 1.20),
    ("2022-11-20", "2022-12-24", 1.20),
    ("2023-11-20", "2023-12-24", 1.15),
    ("2024-11-25", "2024-12-24", 1.15),
    ("2024-05-01", "2024-06-15", 1.80, "RS"),  # enchentes no RS: só destinos RS
    ("2025-11-24", "2025-12-24", 1.15),
]
PEAK_SEASON_TRANSIT = 1.25  # 15/nov–31/dez de qualquer ano

# Inflação acumulada aproximada (IPCA) sobre preço e frete, base 2017 = 1
INFLATION = {2016: 0.97, 2017: 1.00, 2018: 1.04, 2019: 1.08, 2020: 1.13, 2021: 1.24,
             2022: 1.31, 2023: 1.37, 2024: 1.43, 2025: 1.50}

# Itens por pedido (o Olist público tem ~90% com 1 item)
ITEMS_PER_ORDER = {1: 0.865, 2: 0.092, 3: 0.026, 4: 0.010, 5: 0.004, 6: 0.002, 8: 0.001}
EXTRA_ITEM_SAME_PRODUCT = 0.55
EXTRA_ITEM_SAME_SELLER = 0.27   # resto: item independente (outro vendedor possível)

# Recompra (pedido de cliente que já comprou antes), sobe devagar com o tempo
REPEAT_RATE = {2018: 0.030, 2019: 0.032, 2020: 0.035, 2021: 0.040, 2022: 0.042,
               2023: 0.045, 2024: 0.048, 2025: 0.050}

# Vendedores: popularidade log-normal (Gini alto) e entrada/saída ao longo do tempo
SELLER_POP_SIGMA = 1.7
SELLER_START_YEAR = {2016: 0.03, 2017: 0.24, 2018: 0.15, 2019: 0.12, 2020: 0.14,
                     2021: 0.11, 2022: 0.08, 2023: 0.06, 2024: 0.045, 2025: 0.025}
SELLER_CHURN_RATE = 0.25
PRODUCT_POP_SIGMA = 1.2

# Pagamento: probabilidade da forma principal por ano
PAYMENT_MIX = {  # credit, boleto, debit, voucher
    2018: (0.755, 0.205, 0.015, 0.025),
    2019: (0.760, 0.195, 0.020, 0.025),
    2020: (0.765, 0.180, 0.030, 0.025),
    2021: (0.770, 0.165, 0.040, 0.025),
    2022: (0.775, 0.150, 0.050, 0.025),
    2023: (0.780, 0.140, 0.055, 0.025),
    2024: (0.785, 0.130, 0.060, 0.025),
    2025: (0.790, 0.120, 0.065, 0.025),
}
VOUCHER_COMBO_RATE = 0.03
TWO_CARDS_RATE = 0.006
INSTALLMENT_BASE_WEIGHTS = {1: 0.34, 2: 0.13, 3: 0.11, 4: 0.08, 5: 0.06, 6: 0.05, 7: 0.02,
                            8: 0.05, 9: 0.01, 10: 0.13, 12: 0.015, 15: 0.003, 18: 0.002, 24: 0.002}
MIN_INSTALLMENT_VALUE = 15.0

# Status finais "anormais" no período simulado
CANCELED_RATE = 0.0055
UNAVAILABLE_RATE = 0.005
LOST_IN_TRANSIT_RATE = 0.0025

# Avaliações
REVIEW_COVERAGE = 0.985
SCORE_TARGET = {1: 0.115, 2: 0.032, 3: 0.082, 4: 0.193, 5: 0.578}
COMMENT_RATE = {1: 0.88, 2: 0.78, 3: 0.58, 4: 0.32, 5: 0.33}
TITLE_RATE = {1: 0.22, 2: 0.16, 3: 0.12, 4: 0.09, 5: 0.10}

# Sujeira plantada (frações sobre a base indicada)
DIRT = dict(
    installments_zero=12,              # linhas de cartão com parcela 0
    installments_empty=8,              # linhas de cartão com parcela vazia
    delivered_without_date=0.0001,     # dos pedidos entregues simulados
    carrier_before_approved=0.005,     # dos pedidos entregues simulados
    canceled_with_delivery=0.0001,     # de todos os pedidos
    city_variant=0.005,                # clientes e vendedores
    product_zero_weight=0.0005,        # produtos
    payment_cents_diff=0.01,           # pedidos
    payment_voucher_excess=0.001,      # pedidos
    duplicate_review=0.002,            # pedidos com avaliação
)

# Preço mediano por categoria (R$ de 2017) e dispersão log-normal.
CATEGORY_PRICE = {
    "pcs": (1100, 0.45), "eletrodomesticos_2": (420, 0.6), "portateis_casa_forno_e_cafe": (520, 0.5),
    "agro_industria_e_comercio": (130, 0.9), "moveis_escritorio": (210, 0.6), "relogios_presentes": (160, 0.7),
    "climatizacao": (110, 0.8), "pc_gamer": (180, 0.6), "eletroportateis": (150, 0.8),
    "instrumentos_musicais": (100, 0.95), "cool_stuff": (130, 0.7), "malas_acessorios": (120, 0.7),
    "moveis_sala": (130, 0.7), "moveis_quarto": (120, 0.7), "la_cuisine": (150, 0.7),
    "moveis_cozinha_area_de_servico_jantar_e_jardim": (110, 0.7), "construcao_ferramentas_seguranca": (100, 0.8),
    "industria_comercio_e_negocios": (95, 0.9), "moveis_colchao_e_estofado": (100, 0.6),
    "seguros_e_servicos": (100, 0.4), "portateis_cozinha_e_preparadores_de_alimentos": (150, 0.7),
    "beleza_saude": (80, 0.8), "cama_mesa_banho": (80, 0.65), "esporte_lazer": (78, 0.8),
    "perfumaria": (80, 0.7), "bebes": (70, 0.8), "moveis_decoracao": (65, 0.8),
    "informatica_acessorios": (75, 0.85), "automotivo": (70, 0.85), "casa_construcao": (75, 0.8),
    "construcao_ferramentas_iluminacao": (70, 0.8), "casa_conforto": (70, 0.7), "fashion_calcados": (75, 0.6),
    "livros_tecnicos": (75, 0.6), "telefonia_fixa": (70, 0.8), "consoles_games": (60, 0.9),
    "utilidades_domesticas": (60, 0.8), "ferramentas_jardim": (60, 0.8), "brinquedos": (60, 0.8),
    "construcao_ferramentas_construcao": (70, 0.8), "construcao_ferramentas_ferramentas": (60, 0.8),
    "audio": (60, 0.8), "market_place": (60, 0.8), "artes": (60, 0.8), "sinalizacao_e_seguranca": (60, 0.7),
    "fashion_roupa_masculina": (70, 0.6), "papelaria": (50, 0.8), "pet_shop": (50, 0.8),
    "eletrodomesticos": (50, 0.9), "artigos_de_festas": (50, 0.7), "dvds_blu_ray": (50, 0.6),
    "musica": (50, 0.7), "cine_foto": (50, 0.8), "fashion_esporte": (50, 0.6), "livros_importados": (50, 0.6),
    "fashion_roupa_feminina": (50, 0.6), "fashion_roupa_infanto_juvenil": (50, 0.6),
    "cds_dvds_musicais": (55, 0.5), "fashion_underwear_e_moda_praia": (45, 0.6),
    "livros_interesse_geral": (45, 0.6), "construcao_ferramentas_jardim": (50, 0.8),
    "fashion_bolsas_e_acessorios": (40, 0.7), "artigos_de_natal": (40, 0.7), "bebidas": (40, 0.7),
    "artes_e_artesanato": (40, 0.7), "alimentos": (35, 0.7), "fraldas_higiene": (35, 0.6),
    "telefonia": (30, 0.9), "eletronicos": (30, 0.9), "alimentos_bebidas": (30, 0.7),
    "flores": (30, 0.6), "casa_conforto_2": (30, 0.6), "tablets_impressao_imagem": (80, 0.7),
}
DEFAULT_PRICE = (70, 0.8)

# Efeito médio da categoria na satisfação (latente da nota)
CATEGORY_SCORE_EFFECT = {
    "moveis_escritorio": -0.35, "moveis_sala": -0.2, "moveis_decoracao": -0.1, "cama_mesa_banho": -0.12,
    "fashion_roupa_masculina": -0.25, "fashion_roupa_feminina": -0.15, "informatica_acessorios": -0.1,
    "telefonia_fixa": -0.2, "audio": -0.12, "moveis_colchao_e_estofado": -0.15,
    "livros_interesse_geral": 0.3, "livros_tecnicos": 0.25, "livros_importados": 0.3,
    "cds_dvds_musicais": 0.3, "fashion_calcados": 0.1, "flores": 0.2, "alimentos_bebidas": 0.15,
}

# Mudança de mix de categorias no tempo (multiplicador por ano)
CATEGORY_DRIFT = {
    "utilidades_domesticas": {2020: 1.35, 2021: 1.25},
    "informatica_acessorios": {2020: 1.4, 2021: 1.3, 2022: 1.1},
    "moveis_escritorio": {2020: 1.8, 2021: 1.5},
    "eletroportateis": {2020: 1.3, 2021: 1.2},
    "pet_shop": {2020: 1.2, 2021: 1.3, 2022: 1.4, 2023: 1.5, 2024: 1.6, 2025: 1.7},
    "beleza_saude": {2022: 1.1, 2023: 1.15, 2024: 1.2, 2025: 1.25},
    "malas_acessorios": {2020: 0.5, 2021: 0.7},
    "fashion_bolsas_e_acessorios": {2020: 0.8},
    "telefonia_fixa": {2021: 0.7, 2022: 0.6, 2023: 0.5, 2024: 0.4, 2025: 0.35},
    "cds_dvds_musicais": {2019: 0.8, 2020: 0.6, 2021: 0.5, 2022: 0.4, 2023: 0.3, 2024: 0.25, 2025: 0.2},
    "dvds_blu_ray": {2019: 0.8, 2020: 0.6, 2021: 0.5, 2022: 0.4, 2023: 0.3, 2024: 0.25, 2025: 0.2},
}

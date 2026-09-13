"""Configurações do pareamento de grupo controle. Mude aqui, não dentro dos steps."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
# raiz de data-extraction/, dois níveis acima de modeling/modelo_grupo_controle/
RAIZ_PROJETO = BASE_DIR.parent.parent

# --- Entradas ------------------------------------------------------------
IBGE_CSV = RAIZ_PROJETO / "data" / "raw" / "outputs_extraction" / "ibge_municipios.csv"
DATACENTER_FILTRADO_CSV = RAIZ_PROJETO / "data" / "silver" / "datacenter_filtrado.csv"

# Municípios cujo nome vem grafado sem acento no datacentermap e precisa ser
# normalizado antes de casar com o nome oficial do IBGE.
MAPA_NOMES_CIDADE = {"Sao Joao de Meriti": "São João de Meriti"}

# --- step1: cidades similares ---------------------------------------------
# Média das features abaixo nesse intervalo de anos (perfil socioeconômico
# "estável" da cidade, anterior à corrida de data centers 2022+).
ANOS_ANALISE = [2016, 2017, 2018, 2019, 2020, 2021]
FEATURES_CIDADE = [
    "populacao",
    "pib_per_capita",
    "pct_va_servicos",
    "pct_va_industria",
    "pct_va_agropecuaria",
    "pct_impostos",
]
N_SIMILARES = 5          # quantos municípios similares salvar por município
MODO_REGIAO = "mesma"    # "mesma" = KNN só dentro da mesma região; outro valor = Brasil inteiro

MUNICIPIOS_SIMILARES_CSV = RAIZ_PROJETO / "data" / "silver" / "municipios_com_cidades_similares.csv"

# --- step2: grupo de controle (6 pontos ao redor do município similar) ----
PONTOS_EXPANDIDOS_CSV = RAIZ_PROJETO / "data" / "silver" / "datacenter_expandido_6_pontos.csv"
N_PONTOS_CONTROLE = 6           # pontos gerados em círculo ao redor do município similar
INCLINACAO_INICIAL_GRAUS = 0.0  # ponto 1 no Norte (0°)

# --- mapa de conferência (gerar_mapa_pontos_datacenter.py) ------------------
MAPA_HTML = RAIZ_PROJETO / "data" / "silver" / "mapa_datacenters.html"
LADO_QUADRADO_KM = 3      # área de amostragem desenhada ao redor de cada ponto
KM_POR_GRAU_LAT = 111.32

MUNICIPIOS_SIMILARES_CSV.parent.mkdir(parents=True, exist_ok=True)

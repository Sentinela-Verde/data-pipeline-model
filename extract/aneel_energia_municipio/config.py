"""Configurações centrais da estimativa de consumo de energia por município.
Mude aqui, não dentro dos steps."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
# raiz do repo, dois níveis acima de extract/aneel_energia_municipio/
RAIZ_PROJETO = BASE_DIR.parent.parent

FONTE = "aneel_energia_municipio"

# --- Dados Abertos ANEEL (CKAN) ---------------------------------------------
CKAN_BASE_URL = "https://dadosabertos.aneel.gov.br"
CKAN_PACKAGE_SHOW_URL = f"{CKAN_BASE_URL}/api/3/action/package_show"

DATASET_SAMP = "samp"
DATASET_INDQUAL_MUNICIPIO = "indqual-municipio"
DATASET_CONTINUIDADE = "indicadores-coletivos-de-continuidade-dec-e-fec"

# Nomes (slugs) dos recursos parquet de continuidade coletiva (DEC/FEC) — é
# de onde vem o vínculo conjunto-de-unidades-consumidoras -> distribuidora
# (CNPJ/sigla). Cobrem décadas diferentes; usamos as 3 pra maximizar a
# cobertura de conjuntos (um conjunto pode não aparecer numa década se não
# teve indicador reportado nela).
RECURSOS_CONTINUIDADE = [
    "indicadores-continuidade-coletivos-2000-2009.parquet",
    "indicadores-continuidade-coletivos-2010-2019.parquet",
    "indicadores-continuidade-coletivos-2020-2029.parquet",
]

# --- Cache local dos arquivos brutos baixados da ANEEL ----------------------
# Arquivos grandes (SAMP/continuidade) ficam em cache pra não rebaixar toda
# vez que um step rodar de novo.
CACHE_DIR = RAIZ_PROJETO / "data" / "raw" / "aneel_cache"

# --- Saída ------------------------------------------------------------------
OUTPUTS_COMPARTILHADOS = RAIZ_PROJETO / "data" / "raw" / "outputs_extraction"

# Produto do step1: 1 distribuidora (CNPJ) por município.
MUNICIPIO_DISTRIBUIDORA_CSV = OUTPUTS_COMPARTILHADOS / "aneel_municipio_distribuidora.csv"
# Produto do step2: consumo de energia (kWh) por distribuidora x ano.
CONSUMO_DISTRIBUIDORA_CSV = OUTPUTS_COMPARTILHADOS / "aneel_consumo_distribuidora_ano.csv"
# Produto final do step3: consumo ESTIMADO por município x ano (rateio por população).
CSV_FINAL = OUTPUTS_COMPARTILHADOS / f"{FONTE}.csv"

# População por município/ano, produzida por extract/bigquery_ibge/. Usada só
# como peso do rateio (não muda o total da distribuidora, só como ele é
# dividido entre os municípios da área de concessão).
IBGE_MUNICIPIOS_CSV = OUTPUTS_COMPARTILHADOS / "ibge_municipios.csv"

# --- Recorte dos dados --------------------------------------------------
ANO_MINIMO = 2010
ANO_MAXIMO = 2023

# Quais linhas do SAMP contam como "energia efetivamente consumida" (evita
# somar receita/demanda/refaturamento e contar a mesma energia duas vezes).
# Ver README.md > "Como o consumo é calculado" pro raciocínio completo.
# Cada tupla é (NomTipoMercado, DscOpcaoEnergia, DscDetalheMercado).
COMBOS_ENERGIA_CONSUMIDA = [
    ("Regular", "CATIVO", "Energia TE (kWh)"),   # mercado cativo: energia faturada via TE
    ("Regular", "LIVRE", "Energia TUSD (kWh)"),  # mercado livre: só paga TUSD, mas o kWh é o mesmo consumido
]

CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_COMPARTILHADOS.mkdir(parents=True, exist_ok=True)

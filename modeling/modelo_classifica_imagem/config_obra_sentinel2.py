"""Config do fluxo PARALELO usando Sentinel-2 em vez de Landsat como fonte de imagem pra
classificação de obra — ver docstring de
`extract/imagens_satelite/sentinel2/extracao_imagem_sentinel2.py` pro porquê (resolução
nativa de 10m, ~9x mais pixel de textura que o Landsat numa caixa de mesmo tamanho).

Mesma estrutura de `config_obra.py`/`config_obra_300m.py`, só que apontando pros GeoTIFFs
Sentinel-2 e com todo caminho de saída com sufixo `_sentinel2`, pra não encostar em nada dos
fluxos Landsat (500m/300m) — dá pra rodar os três e comparar os resultados sem um sobrescrever
o outro.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RAIZ_PROJETO = BASE_DIR.parent.parent

ENV_PATH = RAIZ_PROJETO / ".env"

# --- Entrada -------------------------------------------------------------
# GeoTIFFs Sentinel-2 + metadata.json gerados por
# extract/imagens_satelite/sentinel2/extraction_sentinel2.py.
RAW_DIR = RAIZ_PROJETO / "data" / "raw" / "imagens_satelite_sentinel2_obra"

REFERENCIA_CSV = RAIZ_PROJETO / "data" / "silver" / "datacenters_referencia.csv"

# --- Saída -----------------------------------------------------------------
PROCESSED_DIR = RAIZ_PROJETO / "data" / "silver" / "cobertura_obra_sentinel2"
OVERLAYS_DIR = RAIZ_PROJETO / "data" / "raw" / "imagens_satelite_sentinel2_obra_overlay"
MODEL_PATH = RAIZ_PROJETO / "data" / "models" / "rf_obra_sentinel2.joblib"

# MapBiomas é 30m nativo — exportado aqui na escala do Sentinel-2 (10m), então cada pixel
# MapBiomas vira um bloco ~3x3 no rótulo-semente (reamostragem, não um gabarito mais fino de
# verdade). Ainda assim é uma segunda opinião melhor que limiar cru — ver labels_mapbiomas.py.
USAR_MAPBIOMAS = True
MAPBIOMAS_LABELS_DIR = RAIZ_PROJETO / "data" / "raw" / "labels_mapbiomas_sentinel2_obra"

# --- Limiares dos rótulos-semente ------------------------------------------
# Ponto de partida = os mesmos valores já calibrados no fluxo Landsat de 500m. A resolução é
# bem mais fina aqui (10m vs 30m) — os índices por pixel tendem a ficar mais "puros" (menos
# mistura de classes num mesmo pixel), então pode valer apertar os limiares depois de olhar
# os primeiros resultados; não assuma que o que funcionou pro Landsat vale igual aqui.
NDVI_VEGETACAO_DENSA = 0.6
SAVI_VEGETACAO_DENSA = 0.5
NDVI_GRAMA_MIN = 0.35
NDVI_NAO_VEGETACAO = 0.2
NDBI_CONSTRUCAO = 0.0
BSI_SOLO_EXPOSTO = 0.1
REDNESS_SOLO_EXPOSTO = 0.03

# --- Parâmetros de treino ----------------------------------------------------
# 9 sites x 11 anos x ~2500px (500m/10m)² por imagem -> bem mais pixel disponível que no
# Landsat (~289px/imagem); N_SAMPLES_PER_CLASS pode ser alto sem risco de esgotar amostra.
N_SAMPLES_PER_CLASS = 3000
TEST_SIZE = 0.25
RANDOM_STATE = 42

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
OVERLAYS_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
MAPBIOMAS_LABELS_DIR.mkdir(parents=True, exist_ok=True)

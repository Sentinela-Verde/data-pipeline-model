"""Roda a extração Sentinel-2 (dedicada à classificação de obra) pra amostra de referência.

Espelha `extract/imagens_satelite/landsat/extraction_landsat.py` — mesma amostra
(`data/silver/datacenters_referencia.csv`), mesmos anos, mesmo tamanho de caixa (500m x 500m)
— só troca o sensor. Saída em pasta própria, sem tocar em nada do fluxo Landsat nem no
pipeline Sentinel-2 original (`extract/imagens_satelite/extraction.py`, usado pelo
`modeling/modelo_impacto`).
"""
import os
from pathlib import Path

import ee
import pandas as pd
from dotenv import load_dotenv

from extracao_imagem_sentinel2 import extract_datacenter_timeseries_sentinel2

# --- Carrega o .env pro ambiente do processo ---
# Este script fica em <raiz>/extract/imagens_satelite/sentinel2/, então subimos 3 níveis
# para chegar na raiz do projeto (data-extraction), onde está o .env.
ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = ROOT_DIR / '.env'
load_dotenv(ENV_PATH)

# --- Autenticação/inicialização do Earth Engine (uma vez por sessão) ---
ee.Authenticate()
PROJECT_ID = os.environ.get('PROJECT_ID')
if not PROJECT_ID:
    raise RuntimeError(
        f"PROJECT_ID não encontrado em {ENV_PATH}. Confira se o arquivo existe e "
        "tem a linha PROJECT_ID=seu-projeto-aqui."
    )
ee.Initialize(project=PROJECT_ID)

# --- Carrega o DataFrame com os pontos ---
# Mesma amostra de referência (ano_operacional conhecido) usada nos fluxos Landsat 500m/300m,
# pra ficar comparável entre sensores.
CSV_PATH = ROOT_DIR / 'data/silver/datacenters_referencia.csv'
df = pd.read_csv(CSV_PATH, sep=';')

YEAR_LIST = [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]
OUT_DIR = ROOT_DIR / 'data/raw/imagens_satelite_sentinel2_obra'

# --- Loop: uma extração por linha do DataFrame ---
metadata_paths = []
erros = []

for _, row in df.iterrows():
    name = row['nome_datacenter']
    lat = row['latitude']
    lon = row['longitude']

    print(f'\n=== Extraindo {name} (lat={lat}, lon={lon}) ===')

    try:
        metadata_path = extract_datacenter_timeseries_sentinel2(
            name_datacenter=name,
            lat=lat,
            lon=lon,
            year_list=YEAR_LIST,
            out_dir=OUT_DIR,
            # buffer_m=250 e scale=10 já são o default -> imagem de 500m x 500m, ~50x50 px.
        )
        metadata_paths.append(metadata_path)
    except Exception as e:
        # Um ponto com erro (ex: sem cena Sentinel-2 limpa no período, comum em 2016/2017,
        # anteriores à cobertura do S2_SR_HARMONIZED) não derruba o loop — só registra.
        print(f'[{name}] ERRO: {e}')
        erros.append((name, str(e)))

# --- Resumo final ---
print(f'\n{len(metadata_paths)}/{len(df)} pontos extraídos com sucesso.')
if erros:
    print(f'{len(erros)} pontos falharam:')
    for name, msg in erros:
        print(f'  - {name}: {msg}')

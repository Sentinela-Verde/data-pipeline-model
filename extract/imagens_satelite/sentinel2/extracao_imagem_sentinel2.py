"""Extração da série temporal Sentinel-2, dedicada à classificação de fase de obra — irmã de
`extract/imagens_satelite/landsat/extracao_imagem_landsat.py`, mas usando Sentinel-2 no lugar
de Landsat.

Por que tentar Sentinel-2 pra isso, além do fluxo Landsat (500m/300m) já existente: a
resolução nativa das bandas óticas do Sentinel-2 é 10m, contra 30m do Landsat. Numa caixa de
mesmo tamanho (500m x 500m, igual ao default do fluxo Landsat), isso dá ~50x50 pixels em vez
de ~17x17 — quase 9x mais pixel de textura pra separar solo exposto/construção do entorno já
urbanizado, que era justamente a suspeita por trás do teste de 300m no Landsat (ver docstring
de `extraction_landsat_300m.py`). Trade-off: Sentinel-2 só tem cobertura de refletância de
superfície (`COPERNICUS/S2_SR_HARMONIZED`) a partir de 2017, com poucas cenas limpas até
~2018 — a série fica mais curta que a do Landsat (que cobre 2016 em diante) nos primeiros anos.

Este módulo é deliberadamente separado de `extract/imagens_satelite/extraction.py` (o
pipeline Sentinel-2 original, usado por `modeling/modelo_impacto` com caixa de 6km e rótulo
WorldCover) — não reaproveita nem sobrescreve nada dele, só reusa a mesma lógica de máscara
de nuvem (`mask_s2_clouds`) já validada ali.

As bandas exportadas (`B2,B3,B4,B8,B11,B12` — azul, verde, vermelho, NIR, SWIR1, SWIR2) usam
a MESMA ordem posicional que `classification_obra.compute_indices_obra` espera (mesma ordem
já usada pro Landsat: `SR_B2,SR_B3,SR_B4,SR_B5,SR_B6,SR_B7`), então o módulo de classificação
de obra funciona sem nenhuma alteração — só aponta pra esta pasta em vez da do Landsat.
"""
import json
import os

import ee
import geemap
import numpy as np
import rasterio

DEFAULT_BANDS = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12']

# Valor por padrão só usado se a função for chamada sem `out_dir` explícito.
RAW_DIR = 'data/raw'


def mask_s2_clouds(image):
    """Máscara de nuvem via QA60 (bits 10=nuvem, 11=cirrus) + normalização pra refletância
    (divide por 10000) — idêntica à de `extract/imagens_satelite/extraction.py`."""
    qa = image.select('QA60')

    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11

    mask = (
        qa.bitwiseAnd(cloud_bit_mask)
        .eq(0)
        .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    )

    return image.updateMask(mask).divide(10000)


def extract_datacenter_timeseries_sentinel2(
    name_datacenter,
    lat,
    lon,
    year_list,
    month_start='05-01',
    month_end='07-30',
    cloud_pct=5,
    buffer_m=250,
    scale=10,
    bands=None,
    out_dir=RAW_DIR,
):
    """Extrai, para cada ano de `year_list`, um compósito Sentinel-2 (mediana das cenas que
    passarem no filtro de nuvem) em torno de (lat, lon), exporta um GeoTIFF por ano em
    `out_dir` e salva um `metadata.json` com os parâmetros usados.

    Com os defaults (buffer_m=250, scale=10) a imagem exportada cobre ~500m x 500m — mesmo
    tamanho de caixa do default do fluxo Landsat (`extraction_landsat.py`), mas a 10m/pixel
    em vez de 30m/pixel (~50x50 px em vez de ~17x17).

    Args:
        name_datacenter (str): Nome usado no nome dos arquivos exportados.
        lat, lon (float): Coordenadas do ponto central.
        year_list (list[int]): Anos para os quais gerar um compósito.
        month_start, month_end (str): Janela de datas dentro do ano, formato 'MM-DD'.
        cloud_pct (float): Filtro de `CLOUDY_PIXEL_PERCENTAGE` (% de nuvem na cena inteira)
            aplicado antes do compósito.
        buffer_m (float): Raio (m) do buffer ao redor do ponto; o bounds() do buffer vira um
            quadrado de lado 2*buffer_m. Default 250 -> quadrado de 500m.
        scale (float): Resolução (m/pixel) da exportação. Default 10 (resolução nativa das
            bandas óticas B2/B3/B4/B8; B11/B12 são nativamente 20m e ficam reamostradas).
        bands (list[str] | None): Bandas a exportar. Default DEFAULT_BANDS.
        out_dir (str): Diretório de saída dos GeoTIFFs e do metadata.json.
    """
    bands = bands or DEFAULT_BANDS
    os.makedirs(out_dir, exist_ok=True)

    for year in year_list:
        dataset = (
            ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            .filterDate(f'{year}-{month_start}', f'{year}-{month_end}')
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_pct))
            .map(mask_s2_clouds)
        )

        # Mesma lógica de robustez adotada no fluxo Landsat: se nenhuma cena sobrar depois
        # do filtro, falha explicitamente em vez de exportar um GeoTIFF preto (dataset.mean()
        # de uma coleção vazia vira uma imagem totalmente mascarada, sem erro nenhum).
        n_cenas = dataset.size().getInfo()
        if n_cenas == 0:
            raise RuntimeError(
                f'Nenhuma cena Sentinel-2 encontrada para {name_datacenter} em {year} '
                f'(janela {month_start} a {month_end}, CLOUDY_PIXEL_PERCENTAGE < {cloud_pct}%). '
                'Aumente cloud_pct ou amplie month_start/month_end (lembre que a cobertura '
                'S2_SR_HARMONIZED só começa em 2017, com poucas cenas limpas até ~2018).'
            )

        center_point = ee.Geometry.Point([lon, lat])
        region = center_point.buffer(buffer_m).bounds()

        image_to_export = dataset.mean().select(bands)

        geemap.ee_export_image(
            image_to_export,
            filename=os.path.join(out_dir, f'{name_datacenter}_{year}.tif'),
            scale=scale,
            region=region,
            file_per_band=False,
        )

        print(f'[{name_datacenter} {year}] Download concluído.')

    metadata = {
        'name_datacenter': name_datacenter,
        'lat': lat,
        'lon': lon,
        'year_list': year_list,
        'bands': bands,
        'buffer_m': buffer_m,
        'image_size_m': buffer_m * 2,
        'scale': scale,
        'crs': 'EPSG:4326',
        'sensor': 'Sentinel-2 SR Harmonized',
    }
    metadata_path = os.path.join(out_dir, f'{name_datacenter}_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f'\nMetadados salvos em {metadata_path}')
    return metadata_path


def tif_to_rgb(tif_path, red_index=3, green_index=2, blue_index=1, vis_max=0.3):
    """Lê um GeoTIFF (bandas na ordem B2,B3,B4,B8,B11,B12) e devolve um array RGB (H, W, 3)
    já normalizado (clip 0-1) para plot com matplotlib."""
    with rasterio.open(tif_path) as src:
        red = src.read(red_index)
        green = src.read(green_index)
        blue = src.read(blue_index)

    rgb = np.dstack([red, green, blue])
    return np.clip(rgb / vis_max, 0, 1)


def export_rgb_jpgs(pasta_entrada=RAW_DIR, pasta_saida='imagens_jpg'):
    """Converte todos os GeoTIFFs de `pasta_entrada` em composições RGB salvas como JPG em
    `pasta_saida`, para inspeção visual rápida da série temporal."""
    import matplotlib.pyplot as plt

    os.makedirs(pasta_saida, exist_ok=True)

    for nome_arquivo in sorted(os.listdir(pasta_entrada)):
        if not nome_arquivo.endswith('.tif'):
            continue

        path = os.path.join(pasta_entrada, nome_arquivo)
        rgb = tif_to_rgb(path)

        nome_saida = os.path.splitext(nome_arquivo)[0] + '.jpg'
        path_saida = os.path.join(pasta_saida, nome_saida)

        plt.figure(figsize=(8, 8))
        plt.imshow(rgb)
        plt.title(nome_arquivo)
        plt.axis('off')
        plt.savefig(path_saida, dpi=150, bbox_inches='tight')
        plt.close()

        print(f'Salvo: {path_saida}')

"""Converte só os GeoTIFFs dos data centers de referência (data/silver/datacenters_referencia.csv)
em JPGs — útil pra conferir visualmente esses casos conhecidos. Espelha
`extract/imagens_satelite/landsat/converte_tif_para_jpg_referencia.py`.

Pasta de saída: data/raw/imagens_satelite_sentinel2_obra_jpg

Como rodar:
    python extract/imagens_satelite/sentinel2/converte_tif_para_jpg_referencia_sentinel2.py
"""
import os
from pathlib import Path

import pandas as pd

from extracao_imagem_sentinel2 import tif_to_rgb

ROOT_DIR = Path(__file__).resolve().parents[3]

REFERENCIA_CSV = ROOT_DIR / 'data/silver/datacenters_referencia.csv'
TIF_DIR = ROOT_DIR / 'data/raw/imagens_satelite_sentinel2_obra'
JPG_DIR = TIF_DIR.parent / f'{TIF_DIR.name}_jpg'


def main():
    import matplotlib.pyplot as plt

    nomes_referencia = pd.read_csv(REFERENCIA_CSV, sep=';')['nome_datacenter'].tolist()
    os.makedirs(JPG_DIR, exist_ok=True)

    convertidos = 0
    for nome in nomes_referencia:
        tifs_do_site = sorted(TIF_DIR.glob(f'{nome}_*.tif'))
        if not tifs_do_site:
            print(f'[{nome}] nenhum .tif encontrado em {TIF_DIR} — rode a extração antes.')
            continue

        for caminho_tif in tifs_do_site:
            rgb = tif_to_rgb(str(caminho_tif))
            caminho_jpg = JPG_DIR / (caminho_tif.stem + '.jpg')

            plt.figure(figsize=(8, 8))
            plt.imshow(rgb)
            plt.title(caminho_tif.name)
            plt.axis('off')
            plt.savefig(caminho_jpg, dpi=150, bbox_inches='tight')
            plt.close()

            print(f'Salvo: {caminho_jpg}')
            convertidos += 1

    print(f'\n{convertidos} imagem(ns) convertida(s) para {JPG_DIR}')


if __name__ == '__main__':
    main()

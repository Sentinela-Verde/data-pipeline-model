"""Treina um Random Forest pra vegetação densa / grama / solo exposto / construção a partir
dos GeoTIFFs Sentinel-2 (`config_obra_sentinel2.RAW_DIR`), e classifica toda a série temporal
de cada data center numa tabela de % por classe/ano — sem gerar gráfico.

Espelha `step_classificacao_obra.py` (Landsat 500m) e `step_classificacao_obra_300m.py`,
trocando só `config_obra` por `config_obra_sentinel2`. Mesma lógica de treino único global
(pixels de todos os data centers/anos disponíveis) e mesmo rótulo-semente híbrido
(MapBiomas + limiar espectral) — ver docstring de `step_classificacao_obra.py` pros detalhes.

`classification_obra.py`/`labels_mapbiomas.py` são compartilhados entre os três fluxos (não
dependem do sensor nem do tamanho da caixa) — só os índices são calculados por POSIÇÃO na
pilha de bandas, e a ordem B2,B3,B4,B8,B11,B12 do Sentinel-2 já bate com a ordem esperada
(azul, verde, vermelho, NIR, SWIR1, SWIR2).

Uso:
    python step_classificacao_obra_sentinel2.py
"""
import functools
import glob
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_obra_sentinel2 as config
from classification_obra import (
    balancear_amostras, build_feature_stack_obra, classify_image,
    compute_class_percentages_obra, extract_seed_samples, load_metadata,
    seed_labels_from_indices, tif_path, train_random_forest_obra,
)

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

if config.USAR_MAPBIOMAS:
    import ee
    from dotenv import load_dotenv

    from labels_mapbiomas import seed_labels_hibrido


def inicializa_earth_engine():
    """Só precisa disso se `config.USAR_MAPBIOMAS=True` — o resto do pipeline (treino sem
    MapBiomas, classificação, %, fases) roda sem Earth Engine."""
    load_dotenv(config.ENV_PATH)
    project_id = os.environ.get('PROJECT_ID')
    if not project_id:
        raise RuntimeError(
            f"USAR_MAPBIOMAS=True precisa de PROJECT_ID em {config.ENV_PATH} (mesma variável "
            "usada em extract/imagens_satelite/sentinel2/extraction_sentinel2.py). Defina "
            "isso ou ponha config.USAR_MAPBIOMAS=False pra treinar só com o limiar espectral."
        )
    ee.Initialize(project=project_id)


def lista_datacenters_disponiveis():
    """Um data center por `<nome_datacenter>_metadata.json` encontrado em config.RAW_DIR."""
    padrao = str(config.RAW_DIR / '*_metadata.json')
    return sorted(Path(p).name.removesuffix('_metadata.json') for p in glob.glob(padrao))


def carrega_mapa_referencia():
    """{nome_datacenter: ano_operacional} pros data centers de referência — usado só pra
    marcar o ano operacional no CSV de saída, não entra no treino."""
    if not config.REFERENCIA_CSV.exists():
        return {}
    ref = pd.read_csv(config.REFERENCIA_CSV, sep=';')
    return dict(zip(ref['nome_datacenter'], ref['ano_operacional']))


def treinar_modelo_global(datacenters):
    """Junta pixels-semente de TODAS as imagens (todos os DCs, todos os anos) e treina um
    único Random Forest reaproveitável pra classificar qualquer imagem da série."""
    seed_espectral_fn = functools.partial(
        seed_labels_from_indices,
        ndvi_vegetacao_densa=config.NDVI_VEGETACAO_DENSA,
        savi_vegetacao_densa=config.SAVI_VEGETACAO_DENSA,
        ndvi_grama_min=config.NDVI_GRAMA_MIN,
        ndvi_nao_vegetacao=config.NDVI_NAO_VEGETACAO,
        ndbi_construcao=config.NDBI_CONSTRUCAO,
        bsi_solo_exposto=config.BSI_SOLO_EXPOSTO,
        redness_solo_exposto=config.REDNESS_SOLO_EXPOSTO,
    )

    X_list, y_list = [], []

    for nome in datacenters:
        meta = load_metadata(nome, str(config.RAW_DIR))
        for ano in meta['year_list']:
            caminho = tif_path(nome, ano, str(config.RAW_DIR))
            if not os.path.exists(caminho):
                continue

            feature_stack, nodata_mask, indices = build_feature_stack_obra(caminho)

            if config.USAR_MAPBIOMAS:
                seed_labels, fonte = seed_labels_hibrido(
                    meta, ano, feature_stack, nodata_mask, indices,
                    str(config.MAPBIOMAS_LABELS_DIR), seed_espectral_fn,
                )
                print(f'  [{nome} {ano}] semente: {fonte}')
            else:
                seed_labels = seed_espectral_fn(indices, nodata_mask)

            X, y = extract_seed_samples(feature_stack, seed_labels)
            if len(y):
                X_list.append(X)
                y_list.append(y)

    if not X_list:
        raise RuntimeError(
            'Nenhum pixel-semente encontrado em nenhuma imagem — os limiares em '
            'config_obra_sentinel2.py provavelmente estão longe demais da realidade das '
            'suas cenas.'
        )

    X_all, y_all = np.concatenate(X_list), np.concatenate(y_list)
    X_bal, y_bal = balancear_amostras(X_all, y_all, n_por_classe=config.N_SAMPLES_PER_CLASS)

    X_train, X_test, y_train, y_test = train_test_split(
        X_bal, y_bal, test_size=config.TEST_SIZE, stratify=y_bal, random_state=config.RANDOM_STATE,
    )
    rf = train_random_forest_obra(X_train, y_train, X_test, y_test)

    joblib.dump(rf, config.MODEL_PATH)
    print(f'Modelo salvo em {config.MODEL_PATH}')
    return rf


def classificar_datacenter(nome, rf, mapa_referencia):
    print(f'\n=== {nome} ===')
    meta = load_metadata(nome, str(config.RAW_DIR))
    ano_operacional = mapa_referencia.get(nome)
    linhas = []

    for ano in meta['year_list']:
        caminho = tif_path(nome, ano, str(config.RAW_DIR))
        if not os.path.exists(caminho):
            print(f'  [{ano}] arquivo não encontrado, pulei.')
            continue

        feature_stack, nodata_mask, _ = build_feature_stack_obra(caminho)
        classified = classify_image(feature_stack, nodata_mask, rf)
        percentuais = compute_class_percentages_obra(classified)

        for classe, pct in percentuais.items():
            linhas.append({
                'name_datacenter': nome, 'ano': ano, 'classe': classe, 'percentual': pct,
                'ano_operacional_referencia': ano_operacional,
            })

        print(f'  [{ano}] classificado.')

    df = pd.DataFrame(linhas)
    if not df.empty:
        df.to_csv(config.PROCESSED_DIR / f'{nome}_cobertura_obra_por_ano.csv', index=False)
    return df


def main():
    datacenters = lista_datacenters_disponiveis()
    if not datacenters:
        print(f'Nenhum *_metadata.json encontrado em {config.RAW_DIR} — rode a extração Sentinel-2 antes.')
        return

    if config.MODEL_PATH.exists():
        print(f'Modelo já treinado encontrado em {config.MODEL_PATH} (apague o arquivo pra retreinar).')
        rf = joblib.load(config.MODEL_PATH)
    else:
        if config.USAR_MAPBIOMAS:
            inicializa_earth_engine()
        print(f'Treinando modelo com pixels-semente de {len(datacenters)} data centers...')
        rf = treinar_modelo_global(datacenters)

    mapa_referencia = carrega_mapa_referencia()
    todos = [classificar_datacenter(nome, rf, mapa_referencia) for nome in datacenters]
    consolidado = pd.concat([df for df in todos if not df.empty], ignore_index=True)

    saida = config.PROCESSED_DIR / 'cobertura_obra_todos_datacenters.csv'
    consolidado.to_csv(saida, index=False)
    print(f"\n{consolidado['name_datacenter'].nunique()} data centers classificados. Consolidado em {saida}")


if __name__ == '__main__':
    main()

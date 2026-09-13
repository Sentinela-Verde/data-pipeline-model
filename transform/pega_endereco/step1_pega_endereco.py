"""Step 1 — corrige/preenche município e UF de cada campus a partir de lat/long,
usando reverse geocoding da Google Geocoding API.

Lê `data/raw/lista_mestra_campi.csv` e, para cada linha, consulta a API com as
colunas `lat`/`lon`, extraindo `municipio_corrigido` e `uf_corrigida` da
resposta. Só geocodifica linhas com `pais == config.FILTRO_PAIS` (default
"BR"); as demais recebem `status_geocode = "PAIS_NAO_BR"` sem chamar a API.

Resiliente a quedas de conexão: salva um checkpoint do CSV de saída a cada
`config.SALVAR_A_CADA` linhas, e ao rodar de novo pula as linhas cujo
`status_geocode` já está em `config.STATUS_RESOLVIDOS` (não reconsulta nem
regasta chamadas já feitas com sucesso).

Uso:
    python step1_pega_endereco.py

Precisa de:
- GOOGLE_MAPS_API_KEY no `.env` da raiz do repo (ver `.env.example`), com a
  Geocoding API habilitada no projeto do Google Cloud.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

import os
import pandas as pd
import requests
from dotenv import load_dotenv


def busca_endereco(lat: float, lon: float, api_key: str) -> dict:
    """Consulta a Geocoding API para um par lat/lon e retorna município e UF.

    Retorna dict com `municipio_corrigido`, `uf_corrigida` e `status_geocode`
    (status bruto da API, ou "ERRO_REDE: ..." se todas as tentativas falharem).
    Tenta de novo (com backoff) em caso de erro de rede transitório.
    """
    resultado = {"municipio_corrigido": None, "uf_corrigida": None, "status_geocode": None}

    if pd.isna(lat) or pd.isna(lon):
        resultado["status_geocode"] = "LAT_LON_AUSENTE"
        return resultado

    params = {
        "latlng": f"{lat},{lon}",
        "key": api_key,
        "language": config.IDIOMA,
    }

    dados = None
    ultimo_erro = None
    for tentativa in range(1, config.MAX_TENTATIVAS + 1):
        try:
            resp = requests.get(config.GEOCODE_URL, params=params, timeout=10)
            resp.raise_for_status()
            dados = resp.json()
            break
        except requests.exceptions.RequestException as e:
            ultimo_erro = e
            if tentativa < config.MAX_TENTATIVAS:
                espera = config.BACKOFF_BASE_SEG * (2 ** (tentativa - 1))
                print(f"    Erro de rede ({e.__class__.__name__}), tentativa "
                      f"{tentativa}/{config.MAX_TENTATIVAS}, aguardando {espera}s...")
                time.sleep(espera)

    if dados is None:
        resultado["status_geocode"] = f"ERRO_REDE: {ultimo_erro}"
        return resultado

    resultado["status_geocode"] = dados.get("status")
    if dados.get("status") != "OK" or not dados.get("results"):
        return resultado

    # Primeiro resultado é o mais específico/preciso para o ponto informado.
    componentes = dados["results"][0]["address_components"]

    for comp in componentes:
        tipos = comp["types"]
        if config.TIPO_MUNICIPIO in tipos or config.TIPO_MUNICIPIO_FALLBACK in tipos:
            resultado["municipio_corrigido"] = comp["long_name"]
        if config.TIPO_UF_SIGLA in tipos:
            resultado["uf_corrigida"] = comp["short_name"]

    return resultado


def carrega_progresso_anterior(output_csv: Path) -> dict:
    """Lê um checkpoint anterior (se existir) e retorna {campus_id: {...}}
    só com as linhas já resolvidas (`config.STATUS_RESOLVIDOS`), pra não
    reconsultar a API nem repagar chamadas já feitas com sucesso."""
    if not Path(output_csv).exists():
        return {}

    df_prev = pd.read_csv(output_csv)
    if "status_geocode" not in df_prev.columns or config.COL_ID not in df_prev.columns:
        return {}

    df_ok = df_prev[df_prev["status_geocode"].isin(config.STATUS_RESOLVIDOS)]
    colunas = ["municipio_corrigido", "uf_corrigida", "status_geocode"]
    return df_ok.set_index(config.COL_ID)[colunas].to_dict("index")


def adicionar_endereco_corrigido(
    df_input: pd.DataFrame, api_key: str, progresso_anterior: dict | None = None,
) -> pd.DataFrame:
    """Adiciona `municipio_corrigido`, `uf_corrigida` e `status_geocode` ao df.

    Pula (sem chamar a API) linhas com `pais != config.FILTRO_PAIS` e linhas
    já presentes em `progresso_anterior` (checkpoint de uma execução anterior).
    Salva um checkpoint em `config.OUTPUT_CSV` a cada `config.SALVAR_A_CADA`
    linhas processadas.
    """
    progresso_anterior = progresso_anterior or {}
    df_resultado = df_input.copy()
    municipios, ufs, status = [], [], []

    total = len(df_resultado)
    n_puladas_pais, n_puladas_checkpoint, n_consultadas = 0, 0, 0

    for i, row in enumerate(df_resultado.itertuples(index=False), start=1):
        campus_id = getattr(row, config.COL_ID)

        if campus_id in progresso_anterior:
            info = progresso_anterior[campus_id]
            n_puladas_checkpoint += 1
        elif config.FILTRO_PAIS and getattr(row, config.COL_PAIS, None) != config.FILTRO_PAIS:
            info = {"municipio_corrigido": None, "uf_corrigida": None, "status_geocode": "PAIS_NAO_BR"}
            n_puladas_pais += 1
        else:
            lat = getattr(row, config.COL_LAT)
            lon = getattr(row, config.COL_LON)
            info = busca_endereco(lat, lon, api_key)
            n_consultadas += 1
            time.sleep(config.PAUSA_ENTRE_CHAMADAS_SEG)

        municipios.append(info["municipio_corrigido"])
        ufs.append(info["uf_corrigida"])
        status.append(info["status_geocode"])

        if i % config.SALVAR_A_CADA == 0 or i == total:
            print(f"  {i}/{total} processados "
                  f"({n_consultadas} consultados, {n_puladas_pais} fora do filtro de país, "
                  f"{n_puladas_checkpoint} já resolvidos)")
            checkpoint = df_resultado.iloc[:i].copy()
            checkpoint["municipio_corrigido"] = municipios
            checkpoint["uf_corrigida"] = ufs
            checkpoint["status_geocode"] = status
            checkpoint.to_csv(config.OUTPUT_CSV, index=False, encoding="utf-8-sig")

    df_resultado["municipio_corrigido"] = municipios
    df_resultado["uf_corrigida"] = ufs
    df_resultado["status_geocode"] = status
    return df_resultado


def main():
    load_dotenv(config.ENV_PATH)
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError(
            f"GOOGLE_MAPS_API_KEY não encontrada. Defina-a no arquivo {config.ENV_PATH} "
            "(veja .env.example na raiz do repo)."
        )

    df = pd.read_csv(config.INPUT_CSV)
    print(f"Lidos {len(df)} registros de {config.INPUT_CSV}")

    progresso_anterior = carrega_progresso_anterior(config.OUTPUT_CSV)
    if progresso_anterior:
        print(f"Checkpoint encontrado: {len(progresso_anterior)} linhas já resolvidas, serão puladas")

    df_corrigido = adicionar_endereco_corrigido(df, api_key, progresso_anterior)

    n_falhas = (~df_corrigido["status_geocode"].isin(config.STATUS_RESOLVIDOS)).sum()
    if n_falhas:
        print(f"Aviso: {n_falhas} linhas com falha (ver coluna status_geocode) — rode de novo pra tentar só essas")

    df_corrigido.to_csv(config.OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"Salvo em {config.OUTPUT_CSV}")


if __name__ == "__main__":
    main()

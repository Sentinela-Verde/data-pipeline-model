"""Helpers pra falar com o portal de Dados Abertos da ANEEL (CKAN).

Os links de download de cada recurso (arquivo) mudam de UUID entre datasets
e às vezes entre atualizações, então em vez de hardcodar URLs, resolvemos o
nome do recurso (ex.: "samp-2022.parquet") pra URL de download toda vez via
`package_show` da API do CKAN — e cacheamos o arquivo baixado localmente.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

import requests


def listar_recursos(dataset_slug: str) -> dict:
    """Retorna {nome_do_recurso: url_de_download} pra um dataset do CKAN da ANEEL."""
    resp = requests.get(config.CKAN_PACKAGE_SHOW_URL, params={"id": dataset_slug}, timeout=30)
    resp.raise_for_status()
    dados = resp.json()
    if not dados.get("success"):
        raise RuntimeError(f"CKAN não retornou sucesso pra dataset '{dataset_slug}': {dados}")

    return {r["name"]: r["url"] for r in dados["result"]["resources"]}


def baixar_com_cache(url: str, nome_arquivo: str) -> Path:
    """Baixa `url` pra `config.CACHE_DIR/nome_arquivo`, ou reaproveita se já existir."""
    destino = config.CACHE_DIR / nome_arquivo
    if destino.exists():
        return destino

    print(f"  Baixando {nome_arquivo}...")
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)

    return destino


def baixar_recurso_do_dataset(dataset_slug: str, nome_recurso: str, nome_arquivo: str = None) -> Path:
    """Resolve `nome_recurso` dentro de `dataset_slug` no CKAN e baixa (com cache).

    `nome_arquivo` (opcional) é o nome do arquivo local em cache — útil quando
    o `name` do recurso no CKAN não tem extensão (ex.: "indqual-municipio").
    """
    recursos = listar_recursos(dataset_slug)
    if nome_recurso not in recursos:
        disponiveis = ", ".join(sorted(recursos)[:10])
        raise RuntimeError(
            f"Recurso '{nome_recurso}' não encontrado no dataset '{dataset_slug}'. "
            f"Alguns recursos disponíveis: {disponiveis}..."
        )
    return baixar_com_cache(recursos[nome_recurso], nome_arquivo or nome_recurso)

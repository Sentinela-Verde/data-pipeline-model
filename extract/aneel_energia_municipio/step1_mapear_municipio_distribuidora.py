"""Step 1 — mapeia cada município brasileiro à distribuidora de energia (CNPJ)
que atende sua área, combinando dois datasets da ANEEL que não se falam
diretamente:

- `indqual-municipio` (dataset "IndQual Município"): liga município a um
  "conjunto de unidades consumidoras" (`IdeConjUnidConsumidoras`) — uma
  unidade geográfica interna da ANEEL, menor que a distribuidora.
- `indicadores-coletivos-de-continuidade-dec-e-fec` (DEC/FEC): reporta, por
  período, qual distribuidora (`SigAgente`/`NumCNPJ`) é dona de cada conjunto
  (`IdeConjUndConsumidoras` — mesma coisa, grafia diferente entre datasets).

Município -> conjunto -> distribuidora dá o vínculo que falta.

Uso:
    python step1_mapear_municipio_distribuidora.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
from aneel_ckan import baixar_recurso_do_dataset

import pandas as pd
import pyarrow.parquet as pq


def carregar_municipio_conjunto() -> pd.DataFrame:
    caminho = baixar_recurso_do_dataset(
        config.DATASET_INDQUAL_MUNICIPIO, "indqual-municipio", "indqual-municipio.csv"
    )
    df = pd.read_csv(caminho, sep=";", encoding="latin1")
    df = df.rename(columns={
        "IdeConjUnidConsumidoras": "id_conjunto",
        "CodMunicipio": "id_municipio",
        "NomMunicipio": "municipio",
        "SigUF": "uf",
    })
    return df[["id_conjunto", "id_municipio", "municipio", "uf"]].drop_duplicates()


def carregar_conjunto_distribuidora() -> pd.DataFrame:
    """Concatena os 3 arquivos de continuidade (décadas diferentes) só com as
    colunas de identificação, pra maximizar a cobertura de conjuntos."""
    partes = []
    for nome_recurso in config.RECURSOS_CONTINUIDADE:
        caminho = baixar_recurso_do_dataset(config.DATASET_CONTINUIDADE, nome_recurso)
        tabela = pq.read_table(caminho, columns=["IdeConjUndConsumidoras", "SigAgente", "NumCNPJ"])
        partes.append(tabela.to_pandas())

    df = pd.concat(partes, ignore_index=True)
    df = df.rename(columns={
        "IdeConjUndConsumidoras": "id_conjunto",
        "SigAgente": "sigla_distribuidora",
        "NumCNPJ": "cnpj_distribuidora",
    })
    df["sigla_distribuidora"] = df["sigla_distribuidora"].str.strip()
    df["id_conjunto"] = df["id_conjunto"].astype("Int64")
    return df.drop_duplicates()


def mapear_municipio_distribuidora(mun_conj: pd.DataFrame, conj_dist: pd.DataFrame) -> pd.DataFrame:
    """Junta município -> conjunto -> distribuidora.

    Um conjunto pode ter mais de uma distribuidora associada ao longo do
    tempo (privatização, fusão) e um município pode ter mais de um conjunto
    — nesses casos, fica com a distribuidora mais frequente entre os
    conjuntos do município (maioria simples), pra garantir 1 distribuidora
    por município no resultado final.
    """
    juncao = mun_conj.merge(conj_dist, on="id_conjunto", how="inner")

    contagem = (
        juncao.groupby(["id_municipio", "municipio", "uf", "cnpj_distribuidora", "sigla_distribuidora"])
        .size()
        .reset_index(name="n_conjuntos")
    )
    contagem = contagem.sort_values("n_conjuntos", ascending=False)
    vencedor = contagem.drop_duplicates(subset="id_municipio", keep="first")

    return vencedor[["id_municipio", "municipio", "uf", "cnpj_distribuidora", "sigla_distribuidora"]] \
        .sort_values(["uf", "municipio"]).reset_index(drop=True)


def main():
    print("Baixando/lendo município -> conjunto (IndQual Município)...")
    mun_conj = carregar_municipio_conjunto()
    print(f"  {len(mun_conj)} vínculos município-conjunto, {mun_conj['id_municipio'].nunique()} municípios")

    print("Baixando/lendo conjunto -> distribuidora (DEC/FEC, 3 décadas)...")
    conj_dist = carregar_conjunto_distribuidora()
    print(f"  {len(conj_dist)} vínculos conjunto-distribuidora, {conj_dist['id_conjunto'].nunique()} conjuntos")

    df_final = mapear_municipio_distribuidora(mun_conj, conj_dist)
    n_sem_match = mun_conj["id_municipio"].nunique() - df_final["id_municipio"].nunique()
    print(f"{len(df_final)} municípios mapeados a uma distribuidora "
          f"({n_sem_match} municípios do IndQual sem distribuidora encontrada)")

    df_final.to_csv(config.MUNICIPIO_DISTRIBUIDORA_CSV, index=False, encoding="utf-8-sig")
    print(f"Salvo em {config.MUNICIPIO_DISTRIBUIDORA_CSV}")


if __name__ == "__main__":
    main()

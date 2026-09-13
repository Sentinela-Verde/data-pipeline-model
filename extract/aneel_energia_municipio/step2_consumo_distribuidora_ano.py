"""Step 2 — soma o consumo de energia elétrica (kWh) por distribuidora/ano, a
partir do SAMP (Sistema de Acompanhamento de Informações de Mercado, ANEEL).

O SAMP registra, na mesma coluna `VlrMercado`, dezenas de métricas diferentes
por linha (energia em kWh, demanda em kW, receita em R$, refaturamentos de
meses anteriores, geração distribuída etc.) — sem filtrar direito, é fácil
somar coisas que não são "energia consumida" ou contar a mesma energia mais
de uma vez. Ver README.md > "Como o consumo é calculado" pra detalhes.

Uso:
    python step2_consumo_distribuidora_ano.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
from aneel_ckan import baixar_recurso_do_dataset

import pandas as pd
import pyarrow.parquet as pq

COLUNAS_NECESSARIAS = [
    "NumCNPJAgenteDistribuidora", "SigAgenteDistribuidora",
    "NomTipoMercado", "DscOpcaoEnergia", "DscDetalheMercado",
    "DatCompetencia", "VlrMercado",
]


def consumo_de_um_ano(ano: int) -> pd.DataFrame:
    caminho = baixar_recurso_do_dataset(config.DATASET_SAMP, f"samp-{ano}.parquet")
    tabela = pq.read_table(caminho, columns=COLUNAS_NECESSARIAS)
    df = tabela.to_pandas()

    mascara = pd.Series(False, index=df.index)
    for tipo_mercado, opcao_energia, detalhe in config.COMBOS_ENERGIA_CONSUMIDA:
        mascara |= (
            (df["NomTipoMercado"] == tipo_mercado)
            & (df["DscOpcaoEnergia"] == opcao_energia)
            & (df["DscDetalheMercado"] == detalhe)
        )
    df_energia = df[mascara].copy()
    df_energia["ano"] = pd.to_datetime(df_energia["DatCompetencia"]).dt.year

    agrupado = (
        df_energia.groupby(["NumCNPJAgenteDistribuidora", "SigAgenteDistribuidora", "ano"])["VlrMercado"]
        .sum()
        .reset_index()
        .rename(columns={
            "NumCNPJAgenteDistribuidora": "cnpj_distribuidora",
            "SigAgenteDistribuidora": "sigla_distribuidora",
            "VlrMercado": "consumo_kwh",
        })
    )
    agrupado["sigla_distribuidora"] = agrupado["sigla_distribuidora"].str.strip()
    return agrupado


def main():
    partes = []
    for ano in range(config.ANO_MINIMO, config.ANO_MAXIMO + 1):
        print(f"Processando SAMP {ano}...")
        partes.append(consumo_de_um_ano(ano))

    df_final = pd.concat(partes, ignore_index=True)
    # Um mesmo CNPJ pode aparecer com siglas diferentes ao longo dos anos
    # (fusões/renomeações) — soma por CNPJ+ano de novo pra garantir 1 linha.
    df_final = (
        df_final.groupby(["cnpj_distribuidora", "ano"], as_index=False)
        .agg(sigla_distribuidora=("sigla_distribuidora", "last"), consumo_kwh=("consumo_kwh", "sum"))
    )

    print(f"{len(df_final)} registros (distribuidora x ano), "
          f"{df_final['cnpj_distribuidora'].nunique()} distribuidoras")

    df_final.to_csv(config.CONSUMO_DISTRIBUIDORA_CSV, index=False, encoding="utf-8-sig")
    print(f"Salvo em {config.CONSUMO_DISTRIBUIDORA_CSV}")


if __name__ == "__main__":
    main()

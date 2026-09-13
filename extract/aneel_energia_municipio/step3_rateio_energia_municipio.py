"""Step 3 — estima o consumo de energia elétrica por MUNICÍPIO/ano, rateando
o consumo de cada distribuidora (step2) entre os municípios da sua área de
concessão (step1), proporcionalmente à população de cada um (IBGE).

IMPORTANTE: isso é uma ESTIMATIVA, não uma medição — distribui o total da
distribuidora por peso populacional, não reflete o consumo real de cada
município dentro da área dela (um polo industrial pequeno em população pode
consumir muito mais energia que uma cidade-dormitório grande). Ver
README.md > "Limitações" antes de usar isso como verdade de campo.

Uso:
    python step3_rateio_energia_municipio.py

Precisa ter rodado antes:
    python step1_mapear_municipio_distribuidora.py
    python step2_consumo_distribuidora_ano.py
E ter `data/raw/outputs_extraction/ibge_municipios.csv` (extract/bigquery_ibge/).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

import pandas as pd


def main():
    municipio_dist = pd.read_csv(config.MUNICIPIO_DISTRIBUIDORA_CSV)
    consumo_dist = pd.read_csv(config.CONSUMO_DISTRIBUIDORA_CSV)
    populacao = pd.read_csv(config.IBGE_MUNICIPIOS_CSV)[["id_municipio", "ano", "populacao"]].drop_duplicates()

    # Um município x um ano x a distribuidora que o atende x a população dele naquele ano.
    base = municipio_dist.merge(populacao, on="id_municipio", how="inner")
    base = base[base["ano"].between(config.ANO_MINIMO, config.ANO_MAXIMO)]

    # População total da área de concessão de cada distribuidora, por ano —
    # denominador do rateio.
    pop_distribuidora_ano = (
        base.groupby(["cnpj_distribuidora", "ano"])["populacao"]
        .sum()
        .reset_index(name="populacao_area_distribuidora")
    )

    base = base.merge(pop_distribuidora_ano, on=["cnpj_distribuidora", "ano"], how="left")
    base = base.merge(consumo_dist[["cnpj_distribuidora", "ano", "consumo_kwh"]],
                       on=["cnpj_distribuidora", "ano"], how="inner")

    base["consumo_estimado_kwh"] = (
        base["consumo_kwh"] * base["populacao"] / base["populacao_area_distribuidora"]
    )
    base = base.rename(columns={"consumo_kwh": "consumo_distribuidora_kwh"})

    colunas_finais = [
        "id_municipio", "municipio", "uf", "ano",
        "sigla_distribuidora", "cnpj_distribuidora",
        "populacao", "populacao_area_distribuidora",
        "consumo_distribuidora_kwh", "consumo_estimado_kwh",
    ]
    df_final = base[colunas_finais].sort_values(["uf", "municipio", "ano"]).reset_index(drop=True)

    print(f"{len(df_final)} registros (município x ano), "
          f"{df_final['id_municipio'].nunique()} municípios, "
          f"{df_final['ano'].nunique()} anos")

    df_final.to_csv(config.CSV_FINAL, index=False, encoding="utf-8-sig")
    print(f"Salvo em {config.CSV_FINAL}")


if __name__ == "__main__":
    main()

"""Extrai consumo de energia elétrica por UF/mês/classe de consumo, via BigQuery
(Base dos Dados), a partir do MME (Ministério de Minas e Energia).

IMPORTANTE — granularidade: a Base dos Dados não tem consumo elétrico por
MUNICÍPIO, só por UF (`br_mme_consumo_energia_eletrica.uf`). Esse extrator
serve pra ter uma aproximação estadual enquanto não houver uma fonte
municipal (ver `extract/aneel_energia_municipio/` pra uma estimativa mais
fina via rateio SAMP por área de concessão das distribuidoras).

Uso:
    python step0a_extract_dados_mme_energia_uf.py

Precisa de:
- PROJECT_ID no `.env` da raiz do repo — projeto do Google Cloud usado só
  pra faturamento das queries (a Base dos Dados em si é pública/gratuita).
- Credenciais do Google Cloud configuradas localmente, ex.:
    gcloud auth application-default login
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

import basedosdados as bd
from dotenv import load_dotenv

QUERY_ENERGIA_UF = f"""
SELECT
  C.ano,
  C.mes,
  C.sigla_uf AS uf,
  U.nome AS nome_uf,
  U.regiao,
  C.tipo_consumo,
  C.consumo,
  C.numero_consumidores

FROM `basedosdados.br_mme_consumo_energia_eletrica.uf` AS C
LEFT JOIN `basedosdados.br_bd_diretorios_brasil.uf` AS U
  ON C.sigla_uf = U.sigla

WHERE C.ano BETWEEN {config.ANO_MINIMO} AND {config.ANO_MAXIMO}
ORDER BY U.regiao, C.sigla_uf, C.ano, C.mes, C.tipo_consumo
"""


def carregar_project_id() -> str:
    load_dotenv(config.ENV_PATH)
    project_id = os.environ.get("PROJECT_ID")
    if not project_id:
        raise RuntimeError(
            f"PROJECT_ID não encontrado. Defina-o no arquivo {config.ENV_PATH} "
            "(veja .env.example na raiz do repo)."
        )
    return project_id


def main():
    project_id = carregar_project_id()

    print(f"Executando extração do consumo de energia elétrica por UF, {config.ANO_MINIMO}-{config.ANO_MAXIMO}...")
    df = bd.read_sql(QUERY_ENERGIA_UF, billing_project_id=project_id)

    print(f"{len(df)} registros (UF x ano x mês x tipo_consumo), {df['uf'].nunique()} UFs")

    df.to_csv(config.CSV_FINAL, index=False, encoding="utf-8-sig")
    print(f"Extração concluída e salva em '{config.CSV_FINAL}'.")


if __name__ == "__main__":
    main()

"""Extrai dados de uso de água por município/ano no Brasil inteiro, via BigQuery
(Base dos Dados), a partir do SNIS-AE (Sistema Nacional de Informações sobre
Saneamento — Água e Esgotos).

Uso:
    python step0a_extract_dados_snis_agua.py

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

# `C.*` traz todas as colunas do SNIS-AE (volume produzido/consumido/faturado,
# perdas, população atendida, índices de atendimento, investimentos etc.) —
# assim não fica engessado numa lista fixa de indicadores de uso de água.
QUERY_SNIS_AGUA = f"""
SELECT
  C.ano,
  B.id_municipio,
  B.nome AS municipio,
  B.sigla_uf AS uf,
  B.nome_regiao AS regiao,
  A.populacao,
  C.* EXCEPT (id_municipio, ano)

FROM `basedosdados.br_mdr_snis.municipio_agua_esgoto` AS C
INNER JOIN `basedosdados.br_bd_diretorios_brasil.municipio` AS B
  ON C.id_municipio = B.id_municipio
LEFT JOIN `basedosdados.br_ibge_populacao.municipio` AS A
  ON C.id_municipio = A.id_municipio AND C.ano = A.ano

WHERE C.ano BETWEEN {config.ANO_MINIMO} AND {config.ANO_MAXIMO}
ORDER BY B.nome_uf, B.nome, C.ano
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

    print(f"Executando extração do SNIS-AE (água e esgoto), {config.ANO_MINIMO}-{config.ANO_MAXIMO}...")
    df = bd.read_sql(QUERY_SNIS_AGUA, billing_project_id=project_id)

    print(f"{len(df)} registros (município x ano), {df['id_municipio'].nunique()} municípios")

    df.to_csv(config.CSV_FINAL, index=False, encoding="utf-8-sig")
    print(f"Extração concluída e salva em '{config.CSV_FINAL}'.")


if __name__ == "__main__":
    main()

"""Configurações centrais da extração. Mude aqui, não dentro do step."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
# raiz do repo — onde ficam a pasta data/ (compartilhada entre coletores) e o
# .env, dois níveis acima de extract/bigquery_mme_energia_uf/
RAIZ_PROJETO = BASE_DIR.parent.parent

FONTE = "mme_energia_uf"  # nome dessa coleta, usado no nome do CSV final

# --- Autenticação BigQuery / Base dos Dados --------------------------------
# PROJECT_ID = projeto do Google Cloud usado só pra faturamento das queries
# (a Base dos Dados em si é pública/gratuita até uma cota generosa; o
# projeto funciona como "conta" pro BigQuery cobrar, se passar da cota).
# Vem do .env na raiz do repo — nunca comitar esse arquivo.
ENV_PATH = RAIZ_PROJETO / ".env"

# --- Saída ------------------------------------------------------------------
# O CSV final é o "produto" dessa coleta e vai pra pasta compartilhada
# data/raw/outputs_extraction/, junto com o resultado de outras coletas.
OUTPUTS_COMPARTILHADOS = RAIZ_PROJETO / "data" / "raw" / "outputs_extraction"
CSV_FINAL = OUTPUTS_COMPARTILHADOS / f"{FONTE}.csv"

# --- Recorte dos dados --------------------------------------------------
# Toda a série mensal disponível na Base dos Dados (`br_mme_consumo_energia_eletrica.uf`).
ANO_MINIMO = 2004
ANO_MAXIMO = 2023

OUTPUTS_COMPARTILHADOS.mkdir(parents=True, exist_ok=True)

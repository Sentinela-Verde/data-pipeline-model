"""Configurações da correção de endereço via Google Geocoding API. Mude aqui, não dentro do step."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
# raiz de data-extraction/, dois níveis acima de transform/pega_endereco/
RAIZ_PROJETO = BASE_DIR.parent.parent

ENV_PATH = RAIZ_PROJETO / ".env"  # precisa de GOOGLE_MAPS_API_KEY

# --- Entrada ---------------------------------------------------------------
INPUT_CSV = RAIZ_PROJETO / "data" / "raw" / "lista_mestra_campi.csv"
COL_ID = "campus_id"  # chave única, usada pra retomar execuções interrompidas
COL_LAT = "lat"
COL_LON = "lon"
COL_PAIS = "pais"

# Geocodifica todas as linhas, de qualquer país. Defina com uma sigla (ex.:
# "BR") pra restringir a esse país só; as demais ficariam com
# status_geocode = "PAIS_NAO_BR" sem chamar a API.
FILTRO_PAIS = None

# --- Saída -------------------------------------------------------------
OUTPUT_DIR = RAIZ_PROJETO / "data" / "silver"
OUTPUT_CSV = OUTPUT_DIR / "lista_metra_endereco_corrigido.csv"

# --- Geocoding API (reverse geocoding) --------------------------------------
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
IDIOMA = "pt-BR"

# Tipos de componente de endereço usados pra extrair município e estado da
# resposta da API (ver docs.: https://developers.google.com/maps/documentation/geocoding/requests-geocoding#Types).
TIPO_MUNICIPIO = "administrative_area_level_2"  # fallback: "locality"
TIPO_MUNICIPIO_FALLBACK = "locality"
TIPO_UF_SIGLA = "administrative_area_level_1"  # short_name = sigla (ex.: "SP")

# Pausa entre chamadas pra não estourar o rate limit da API (requisições/segundo).
PAUSA_ENTRE_CHAMADAS_SEG = 0.05

# Resiliência a falhas de rede transitórias (ex.: ConnectionResetError).
MAX_TENTATIVAS = 3
BACKOFF_BASE_SEG = 2  # dobra a cada nova tentativa: 2s, 4s, 8s...

# Salva um checkpoint do CSV de saída a cada N linhas processadas, pra não
# perder progresso (nem repagar chamadas já feitas) se o script cair no meio.
SALVAR_A_CADA = 50

# Status de status_geocode considerados "resolvidos" — ao rodar de novo, o
# script pula linhas que já têm um desses (não reconsulta a API pra elas).
STATUS_RESOLVIDOS = {"OK", "PAIS_NAO_BR", "LAT_LON_AUSENTE"}

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

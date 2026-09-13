# pega_endereco — raw → silver do endereço corrigido dos campi

Passo de `transform/`: pega `data/raw/lista_mestra_campi.csv` e, para cada
linha, faz *reverse geocoding* (lat/long → endereço) via
[Google Geocoding API](https://developers.google.com/maps/documentation/geocoding)
pra obter município e UF a partir das coordenadas — útil quando os campos
`municipio`/`uf` originais do CSV vêm ausentes ou digitados de forma
inconsistente.

## Como funciona

Para cada linha, consulta a Geocoding API com `lat`/`lon` (de qualquer país
da lista) e extrai dos `address_components` da resposta:

- `municipio_corrigido` — do componente `administrative_area_level_2` (nome
  oficial do município); se ausente, usa `locality` como fallback.
- `uf_corrigida` — sigla (`short_name`) do componente
  `administrative_area_level_1`.
- `status_geocode` — status da linha: `OK`, `ZERO_RESULTS` (retorno da API),
  `LAT_LON_AUSENTE` (sem coordenada) ou `ERRO_REDE: ...` (falhou mesmo após
  retries).

Dá pra restringir a um único país de novo setando `config.FILTRO_PAIS` (ex.:
`"BR"`) — linhas fora dele ficam com `status_geocode = "PAIS_NAO_BR"` sem
chamar a API.

## Resiliência a quedas de conexão

- Cada chamada tenta até `config.MAX_TENTATIVAS` vezes (backoff exponencial)
  antes de desistir de uma linha — cobre falhas de rede transitórias
  (ex.: `ConnectionResetError` no meio de uma sequência longa de requisições).
- O CSV de saída é salvo como **checkpoint** a cada `config.SALVAR_A_CADA`
  linhas processadas, não só no final.
- Rodar o script de novo **retoma de onde parou**: linhas cujo
  `status_geocode` já é `OK`, `PAIS_NAO_BR` ou `LAT_LON_AUSENTE` no CSV de
  saída existente são puladas (não reconsultam a API nem repagam a chamada);
  só linhas com falha (`ERRO_REDE: ...` ou `ZERO_RESULTS`) são tentadas de novo.

## Como rodar

```bash
cd data-extraction/transform/pega_endereco
pip install -r requirements.txt
python step1_pega_endereco.py
```

Precisa de **`GOOGLE_MAPS_API_KEY`** no `.env` da raiz do repo (ver
`.env.example`), com a **Geocoding API** habilitada e faturamento ativo no
projeto do Google Cloud correspondente.

- **Entrada:** `../../data/raw/lista_mestra_campi.csv`
- **Saída:** `../../data/silver/lista_metra_endereco_corrigido.csv` — mesmas
  colunas de entrada + `municipio_corrigido`, `uf_corrigida`, `status_geocode`.

## Observações

- Uma chamada de API por linha, com uma pequena pausa entre elas
  (`config.PAUSA_ENTRE_CHAMADAS_SEG`) pra não estourar rate limit. Para um CSV
  grande, isso pode demorar e consumir cota paga da API — confira o tamanho de
  `lista_mestra_campi.csv` antes de rodar.
- Linhas com `lat`/`lon` ausentes não chamam a API (`status_geocode =
  "LAT_LON_AUSENTE"`).

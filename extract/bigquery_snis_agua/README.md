# bigquery_snis_agua — coleta da Base dos Dados / SNIS-AE (BigQuery)

Extração de dados de uso de água (produção, consumo, perdas, atendimento) por
**município e ano**, para o Brasil inteiro, via BigQuery, usando a
[Base dos Dados](https://basedosdados.org/). É uma das coletas dentro de
`data-extraction/extract/` — ver o [README da raiz](../../README.md) pra
entender como as coletas se encaixam (pasta `data/raw/` compartilhada).

## Ideia geral

A Base dos Dados já publica o **SNIS-AE** (Sistema Nacional de Informações
sobre Saneamento — Diagnóstico Água e Esgotos, Ministério das Cidades/MDR)
tratado no BigQuery, então não tem scraping aqui — é uma extração direta via
SQL, usando a lib `basedosdados` (`bd.read_sql`):

- `QUERY_SNIS_AGUA` — todas as colunas de `br_mdr_snis.municipio_agua_esgoto`
  (`C.*`, sem engessar numa lista fixa de indicadores — traz volume
  produzido/consumido/faturado, perdas, população atendida, índices de
  atendimento etc.), uma linha por município x ano, juntada com nome do
  município/UF/região (`br_bd_diretorios_brasil.municipio`) e população
  (`br_ibge_populacao.municipio`).

Diferente do `extract/bigquery_ibge/`, aqui não tem filtro de UF — pega **o
Brasil inteiro**, dentro da janela `config.ANO_MINIMO`-`config.ANO_MAXIMO`.

## Autenticação

Mesmo esquema do `extract/bigquery_ibge/` — duas coisas diferentes, não
confundir:

1. **`PROJECT_ID`** — projeto do Google Cloud usado só pra *faturamento* das
   queries no BigQuery (a Base dos Dados em si é pública e cabe na cota
   gratuita do BigQuery pra a maioria dos usos). Vem do `.env` na raiz do
   repo — ver `.env.example`. **Nunca comitar o `.env`**.
2. **Credenciais do Google Cloud** — o `basedosdados` autentica via
   Application Default Credentials do `gcloud`, não por uma chave no `.env`:

   ```bash
   gcloud auth application-default login
   ```

## Como rodar

```bash
cd data-extraction/extract/bigquery_snis_agua
pip install -r requirements.txt
python step0a_extract_dados_snis_agua.py
```

## Saída

- `../../data/raw/outputs_extraction/snis_agua_municipios.csv` — um
  município x ano por linha, `utf-8-sig` (abre certo no Excel). Colunas:

  | Grupo | Colunas |
  |---|---|
  | Identificação | `municipio`, `uf`, `regiao`, `id_municipio`, `ano` |
  | Demografia | `populacao` |
  | SNIS-AE | todas as demais colunas de `br_mdr_snis.municipio_agua_esgoto` (varia por ano — nem todo município reporta todos os indicadores em todo ano) |

  A série vai de `config.ANO_MINIMO` (hoje `2010`) até `config.ANO_MAXIMO`
  (hoje `2023`) — ajuste no `config.py` se uma coleta mais recente já
  estiver disponível na Base dos Dados.

## Observação

Nem todo município preenche o SNIS todo ano (adesão é do prestador de
serviço, não é censitária) — espere linhas com muitos campos nulos para
municípios pequenos ou anos mais antigos.

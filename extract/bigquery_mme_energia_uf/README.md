# bigquery_mme_energia_uf — coleta da Base dos Dados / MME (BigQuery)

Extração do consumo de energia elétrica na rede, por **UF, mês e classe de
consumo**, via BigQuery, usando a [Base dos Dados](https://basedosdados.org/).
É uma das coletas dentro de `data-extraction/extract/` — ver o
[README da raiz](../../README.md) pra entender como as coletas se encaixam
(pasta `data/raw/` compartilhada).

## ⚠️ Granularidade: só existe por UF, não por município

Pesquisei a fundo na Base dos Dados (metadados via API, não só busca) e **não
existe tabela de consumo elétrico por município** lá — só
`basedosdados.br_mme_consumo_energia_eletrica.uf`, em nível **estadual**,
mensal, quebrado por classe (`tipo_consumo`: residencial, industrial,
comercial, outros — rural/serviço público/iluminação pública).

Isso significa que, se usar essa fonte pra estimar consumo "por município",
todo município de uma UF herda o mesmo valor estadual — não captura variação
municipal real. É útil como aproximação rápida ou como controle de nível
estadual, mas não substitui um dado municipal de verdade.

Pra chegar mais perto do município, ver `extract/aneel_energia_municipio/`
— rateia o consumo do SAMP (ANEEL) por distribuidora entre os municípios da
área de concessão dela, proporcional à população (também uma estimativa, não
uma medição real, mas mais fina que o dado por UF).

## Ideia geral

A Base dos Dados publica o `br_mme_consumo_energia_eletrica.uf` tratado no
BigQuery — extração direta via SQL, usando a lib `basedosdados`
(`bd.read_sql`):

- `QUERY_ENERGIA_UF` — `consumo` (MWh) e `numero_consumidores`, por
  `sigla_uf` x `ano` x `mes` x `tipo_consumo`, juntado com nome da UF e
  região (`br_bd_diretorios_brasil.uf`).

Cobertura confirmada na Base dos Dados: **2004-2023, mensal** (ver
`config.ANO_MINIMO`/`config.ANO_MAXIMO`).

## Autenticação

Mesmo esquema das outras coletas — duas coisas diferentes, não confundir:

1. **`PROJECT_ID`** — projeto do Google Cloud usado só pra *faturamento* das
   queries no BigQuery. Vem do `.env` na raiz do repo — ver `.env.example`.
   **Nunca comitar o `.env`**.
2. **Credenciais do Google Cloud** — Application Default Credentials do
   `gcloud`:

   ```bash
   gcloud auth application-default login
   ```

## Como rodar

```bash
cd data-extraction/extract/bigquery_mme_energia_uf
pip install -r requirements.txt
python step0a_extract_dados_mme_energia_uf.py
```

## Saída

- `../../data/raw/outputs_extraction/mme_energia_uf.csv` — uma linha por
  UF x ano x mês x tipo_consumo, `utf-8-sig`. Colunas: `ano`, `mes`, `uf`,
  `nome_uf`, `regiao`, `tipo_consumo`, `consumo` (MWh), `numero_consumidores`.

Pra agregar num total anual por UF (somando os meses e classes):

```python
import pandas as pd
df = pd.read_csv("../../data/raw/outputs_extraction/mme_energia_uf.csv")
anual_uf = df.groupby(["uf", "ano"], as_index=False)["consumo"].sum()
```

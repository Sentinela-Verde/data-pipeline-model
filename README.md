# Pipeline de dados do Sentinela Verde

Repositório com todas as etapas do processamento de dados do projeto, da
coleta bruta até o dado pronto pra análise: **extração → transformação →
modelagem → analytics**. Cada etapa é uma pasta própria na raiz, e o dado
percorre as camadas em `data/` (`raw` → `silver` → `gold`) conforme passa por
elas.

```
data-extraction/
├── extract/                        # ETAPA 1: coleta de dado bruto
│   ├── scraping_datacentermap/     # coleta: scraping do datacentermap.com
│   ├── bigquery_ibge/              # coleta: Base dos Dados / IBGE (BigQuery)
│   ├── bigquery_mme_energia_uf/    # coleta: consumo de energia por UF (Base dos Dados / MME)
│   ├── bigquery_snis_agua/         # coleta: dados de água por município (Base dos Dados / SNIS-AE)
│   ├── aneel_energia_municipio/    # coleta: consumo de energia estimado por município (ANEEL)
│   └── imagens_satelite/           # coleta: série Sentinel-2 + Landsat via Google Earth Engine
├── transform/                      # ETAPA 2: raw -> silver
│   ├── filtra_datacenter/          # filtra os data centers elegíveis pro estudo
│   └── pega_endereco/              # corrige município/UF por reverse geocoding
├── modeling/                       # ETAPA 3: modelagem sobre o dado tratado
│   ├── modelo_grupo_controle/      # pareia cada data center com um grupo de controle
│   ├── modelo_classifica_imagem/   # classifica cobertura do solo a partir do satélite
│   └── modelo_impacto/             # mede o impacto da chegada do data center
├── analytics/                      # ETAPA 4: análises/consumo final
├── notebooks_antigos/              # notebooks originais, arquivados (ver README próprio)
└── data/                           # dado em trânsito entre as etapas
    ├── raw/                        # dado bruto de todas as coletas, uma pasta por fonte
    │   ├── datacentermap/
    │   ├── imagens_satelite/       #   GeoTIFFs Sentinel-2/Landsat + metadata.json por data center
    │   ├── labels/                 #   rótulos de referência (WorldCover + vias OSM)
    │   └── outputs_extraction/     #   CSVs finais de todas as coletas
    ├── silver/                     # dado tratado/normalizado
    │   ├── datacenter_filtrado.csv           # saída de transform/filtra_datacenter
    │   ├── municipios_com_cidades_similares.csv  # saída de modelo_grupo_controle (step1)
    │   ├── datacenter_expandido_6_pontos.csv     # saída de modelo_grupo_controle (step2)
    │   ├── cobertura_solo/                   # saída de modelo_classifica_imagem
    │   └── consolidado_impacto_modelo.csv    # painel de entrada de modelo_impacto (ver lacuna no README dele)
    ├── gold/                       # dado pronto pra consumo final
    │   └── modelo_impacto/         #   resultados do Estágio 1/2 do modelo de impacto
    └── models/                     # modelos treinados (.joblib) de modelo_classifica_imagem
```

## Etapas do pipeline

1. **`extract/`** — coletas independentes (scraping, API, satélite), cada uma
   na sua própria pasta. Detalhes na seção [Coletas](#coletas) abaixo.
2. **`transform/`** — limpeza, normalização e filtro do que está em
   `data/raw/` pra produzir `data/silver/`. Ver
   [`transform/filtra_datacenter`](transform/filtra_datacenter/README.md) e
   [`transform/pega_endereco`](transform/pega_endereco/README.md) (corrige
   município/UF por reverse geocoding).
3. **`modeling/`** — modelagem (pareamento, classificação de imagem, modelo
   de impacto) em cima do dado de `data/silver/`. Ver [Modelagem](#modelagem)
   abaixo — os três módulos rodam **em sequência**, cada um alimentando o
   próximo.
4. **`analytics/`** — análises e artefatos de consumo final, a partir de
   `data/silver/` e/ou `data/gold/` (por ora, um notebook de exploração e CSVs
   de apoio).

## Convenção pras coletas (`extract/`)

Cada coleta é uma pasta própria dentro de `extract/` (`scraping_datacentermap/`,
`bigquery_ibge/`, `imagens_satelite/`, ...) com seu próprio código, `config.py`
e (se precisar) `requirements.txt` — sem compartilhar código entre coletas. O
que é compartilhado é só a **saída**, guardada fora de `extract/`, em `data/raw/`:

- **`data/raw/<fonte>/...`** — dado bruto extraído por aquela coleta, o mais
  próximo possível do que a fonte devolveu (JSON pequeno, GeoTIFF, etc.).
  Também costuma funcionar como cache incremental — ver o README de cada
  coleta pra saber se e como.
- **`data/raw/outputs_extraction/<fonte>_<algo>.csv`** — o(s) CSV(s) finais e
  prontos pra uso de cada coleta tabular, já limpos/mesclados. É o que a etapa
  `transform/` deveria consumir.

CSVs intermediários que só interessam a uma coleta (ex.:
`extract/scraping_datacentermap/output/regioes.csv`) ficam dentro da própria
pasta da coleta, não em `data/raw/`.

## Coletas

| Pasta | Fonte | Status | Saída |
|---|---|---|---|
| `extract/scraping_datacentermap/` | datacentermap.com (Selenium) | pronta — [README](extract/scraping_datacentermap/README.md) | `data/raw/outputs_extraction/datacentermap_datacenters.csv` |
| `extract/bigquery_ibge/` | Base dos Dados / IBGE (BigQuery) | pronta — [README](extract/bigquery_ibge/README.md) | `data/raw/outputs_extraction/ibge_municipios.csv` |
| `extract/bigquery_mme_energia_uf/` | Base dos Dados / MME (BigQuery) — energia por UF | pronta — [README](extract/bigquery_mme_energia_uf/README.md) | `data/raw/outputs_extraction/` |
| `extract/bigquery_snis_agua/` | Base dos Dados / SNIS-AE (BigQuery) — água por município | pronta — [README](extract/bigquery_snis_agua/README.md) | `data/raw/outputs_extraction/` |
| `extract/aneel_energia_municipio/` | ANEEL — consumo de energia **estimado** por município | pronta — [README](extract/aneel_energia_municipio/README.md) | `data/raw/outputs_extraction/aneel_consumo_distribuidora_ano.csv` |
| `extract/imagens_satelite/` | Sentinel-2 e Landsat (Google Earth Engine) | pronta — [README](extract/imagens_satelite/README.md) | `data/raw/imagens_satelite/*.tif` + `metadata.json` |

Cada pasta de coleta tem seu próprio README com o "como rodar" específico. A
pasta `extract/imagens_satelite/` tem dois fluxos irmãos — Sentinel-2 (o
principal) e [Landsat](extract/imagens_satelite/landsat/README.md), este
usado também num teste paralelo de classificação com
[Sentinel-2](extract/imagens_satelite/sentinel2/README.md) — ver README de
cada um.

## Modelagem

Os três módulos de `modeling/` rodam em sequência — a saída de um é a entrada
do próximo — e cada um tem seu próprio README com o pipeline interno,
parâmetros e saídas detalhadas:

| Ordem | Pasta | O que faz | Entrada principal | Saída principal |
|---|---|---|---|---|
| 1 | [`modelo_grupo_controle/`](modeling/modelo_grupo_controle/README.md) | pareia cada data center com um grupo de controle (municípios similares + pontos ao redor) | `data/silver/datacenter_filtrado.csv` | `data/silver/datacenter_expandido_6_pontos.csv` |
| 2 | [`modelo_classifica_imagem/`](modeling/modelo_classifica_imagem/README.md) | classifica a cobertura do solo (vegetação/água/construção/estrada) em cada ano da série de satélite | GeoTIFFs de `extract/imagens_satelite/` | `data/silver/cobertura_solo/*.csv` |
| 3 | [`modelo_impacto/`](modeling/modelo_impacto/README.md) | mede o efeito da chegada do data center nas variáveis de satélite/clima/socioeconômicas | `data/silver/consolidado_impacto_modelo.csv` (ver lacuna no README) | `data/gold/modelo_impacto/*` |

`modelo_impacto/guia_estrutura_dados_modelo_impacto.md` é a referência
conceitual (unidade de observação, `tratado`, `horizonte`, ano de referência,
grupo de controle) usada pelo módulo 3 — vale ler antes de mexer nele.

## `notebooks_antigos/`

Os notebooks Jupyter que originaram os módulos de `extract/imagens_satelite`,
`transform/filtra_datacenter` e `modeling/` foram convertidos em scripts
(`config.py` + `stepN_*.py`, seguindo a mesma convenção das coletas) e os
`.ipynb` originais ficaram arquivados em `notebooks_antigos/` só de
referência — é uma pasta temporária, o plano é mover esses notebooks pra fora
deste repositório. Ver o [README de lá](notebooks_antigos/README.md).

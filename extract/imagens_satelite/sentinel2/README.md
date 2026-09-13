# imagens_satelite/sentinel2 — teste paralelo com Sentinel-2 pra classificação de obra

Terceira via, separada, pra detectar fase de obra (pré-obra/início/durante/fim) a partir de
satélite — ao lado dos fluxos Landsat de
[500m](../landsat/README.md#teste-inicial-com-amostra-de-referência) e
[300m](../landsat/README.md#teste-paralelo-imagem-menor-300m-x-300m), sem sobrescrever
nenhum dos dois. Usa Sentinel-2 (`COPERNICUS/S2_SR_HARMONIZED`) em vez de Landsat.

## Por que tentar Sentinel-2 aqui

A resolução nativa das bandas óticas do Sentinel-2 é 10m, contra 30m do Landsat. Numa caixa
de mesmo tamanho (500m x 500m, igual ao default do fluxo Landsat), isso dá ~50x50 pixels em
vez de ~17x17 — quase 9x mais pixel de textura por imagem, o que ajuda justamente no problema
que motivou o teste de 300m no Landsat (a caixa pegando entorno já urbanizado em vez de só o
prédio do data center). Ver docstring de
[`extracao_imagem_sentinel2.py`](extracao_imagem_sentinel2.py) pro raciocínio completo.

Trade-off: a cobertura de refletância de superfície do Sentinel-2 (`S2_SR_HARMONIZED`) só
começa em 2017, com poucas cenas limpas até ~2018 — espere falhas explícitas (erro, não
imagem preta) pros anos 2016/2017 em vários sites.

## Como funciona

Mesma amostra de referência (`data/silver/datacenters_referencia.csv`), mesmos anos, mesmo
tamanho de caixa (500m x 500m) do fluxo Landsat de 500m — só troca o sensor, pra ficar
comparável diretamente. `classification_obra.py`/`deteccao_fases_obra_sentinel2.py`
(em `modeling/modelo_classifica_imagem/`) reaproveitam a MESMA lógica de classificação e de
decisão de fase já usada pro Landsat — os índices espectrais são calculados por posição na
pilha de bandas (azul, verde, vermelho, NIR, SWIR1, SWIR2), e a ordem `B2,B3,B4,B8,B11,B12`
do Sentinel-2 já bate com essa convenção, sem precisar de nenhuma adaptação.

### Passo 1 — baixar os GeoTIFFs da amostra de referência

```bash
cd extract/imagens_satelite/sentinel2
python extraction_sentinel2.py
```

Baixa um `.tif` por (data center de referência, ano) em
`data/raw/imagens_satelite_sentinel2_obra/`, mais um `_metadata.json` por data center.

### Passo 2 — gerar os JPGs pra conferência visual

```bash
python converte_tif_para_jpg_referencia_sentinel2.py
```

Salva em `data/raw/imagens_satelite_sentinel2_obra_jpg/`.

### Passo 3 — treinar e classificar

```bash
cd ../../../modeling/modelo_classifica_imagem
python step_classificacao_obra_sentinel2.py
```

### Passo 4 — detectar as fases de obra

```bash
python deteccao_fases_obra_sentinel2.py
```

Saídas em `data/silver/cobertura_obra_sentinel2/`:
- `<nome>_cobertura_obra_por_ano.csv` (passo 3) e `cobertura_obra_todos_datacenters.csv`
  consolidado.
- `fases_obra_por_ano.csv` e `fases_obra_resumo_por_datacenter.csv` (passo 4).

## Pré-requisitos

Mesmos do fluxo Landsat: `PROJECT_ID` no `.env` da raiz do repo, autenticação Earth Engine já
feita (`ee.Authenticate()`), `pip install -r ../requirements.txt`.

## Arquivos

- `extracao_imagem_sentinel2.py` — funções reutilizáveis: extração, máscara de nuvem, RGB
  (mesma máscara `mask_s2_clouds` do pipeline Sentinel-2 original, só reaproveitada aqui).
- `extraction_sentinel2.py` — script que roda a extração pra amostra de referência.
- `converte_tif_para_jpg_referencia_sentinel2.py` — conversão TIF→JPG da amostra.

Deliberadamente separado tanto de `extract/imagens_satelite/extraction.py` (pipeline
Sentinel-2 original, caixa de 6km, rótulo WorldCover, usado por `modeling/modelo_impacto`)
quanto de `extract/imagens_satelite/landsat/` — nenhum arquivo é compartilhado nem
sobrescrito entre os três.

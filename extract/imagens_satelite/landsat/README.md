# imagens_satelite/landsat — extração da série temporal Landsat 8/9

Equivalente ao pipeline Sentinel-2 (ver [README da pasta acima](../README.md)), mas usando
Landsat Collection 2 Level 2 (Surface Reflectance) — útil pra série histórica mais longa e
como alternativa quando o Sentinel-2 não cobre o período (o produto de refletância de
superfície do Sentinel-2 só existe a partir de 2017, e com cobertura fraca até ~2018).

## Como funciona

Para cada ponto (`nome_datacenter`, `latitude`, `longitude`) e cada ano de `YEAR_LIST`:

1. Filtra `LANDSAT/LC08/C02/T1_L2` + `LANDSAT/LC09/C02/T1_L2` (mescladas) pela janela
   `abr-ago` e por `CLOUD_COVER < 10%`.
2. Mascara nuvem/sombra/cirrus pixel a pixel via `QA_PIXEL` e aplica o fator de escala
   oficial das bandas SR (`mask_scale_landsat`).
3. Se nenhuma cena sobrar depois do filtro, a extração **falha com erro explícito**
   (em vez de silenciosamente exportar um GeoTIFF preto) — o loop principal captura isso e
   segue pros próximos pontos, mas fica registrado no resumo final.
4. Tira a média temporal das cenas que sobraram e recorta num buffer de 250m de raio
   (→ 500m x 500m) ao redor do ponto.
5. Exporta um GeoTIFF com as bandas `SR_B2,SR_B3,SR_B4,SR_B5,SR_B6,SR_B7` (azul, verde,
   vermelho, NIR, SWIR1, SWIR2 — mesma ordem espectral usada no Sentinel-2) a 30m/pixel
   (resolução nativa do Landsat).

Salva um `<nome_datacenter>_metadata.json` por ponto com os parâmetros usados — consumido
por [`modeling/modelo_classifica_imagem`](../../../modeling/modelo_classifica_imagem/README.md).

## Pré-requisitos

```bash
cd data-extraction/extract/imagens_satelite/landsat
pip install -r ../requirements.txt   # mesmas libs do pipeline Sentinel-2 (ee, geemap, rasterio...)
```

`PROJECT_ID` no `.env` da raiz do repo (projeto do Google Cloud com a API do Earth Engine
habilitada). Na primeira vez, `ee.Authenticate()` abre o login do Earth Engine no navegador.

## Teste inicial com amostra de referência

Antes de rodar pra base inteira (centenas de data centers, cada um levando minutos por causa
das chamadas ao Earth Engine), valide o pipeline numa amostra pequena de data centers cujo
**ano operacional já é conhecido** — dá pra conferir visualmente se o modelo de classificação
detecta o fim da obra perto do ano real em que o site entrou em operação.

Essa amostra vive em [`data/silver/datacenters_referencia.csv`](../../../data/silver/datacenters_referencia.csv)
(`nome_datacenter;latitude;longitude;ano_operacional`) e é o que `extraction_landsat.py` usa
por padrão hoje.

### Passo 1 — baixar os GeoTIFFs da amostra de referência

```bash
python extraction_landsat.py
```

Baixa um `.tif` por (data center de referência, ano de `YEAR_LIST`) em
`data/raw/imagens_satelite_landsat/`, mais um `_metadata.json` por data center. Um ponto com
erro (ex: sem cena limpa naquele ano) não derruba o loop — aparece no resumo final impresso.

### Passo 2 — gerar os JPGs só dessa amostra (conferência visual)

```bash
python converte_tif_para_jpg_referencia.py
```

Converte só os `.tif` cujo nome bate com algum `nome_datacenter` do CSV de referência —
mesmo que a pasta de entrada já tenha outros data centers baixados depois. Salva em
`data/raw/imagens_satelite_landsat_jpg/`. Use isso pra olhar a olho nu a composição RGB de
cada ano antes de confiar em qualquer % que o modelo calcular.

(Existe também `converte_tif_para_jpg.py`, que converte **tudo** que estiver na pasta de
entrada — útil quando já tiver rodado a base inteira.)

### Passo 3 — treinar e classificar

```bash
cd ../../../modeling/modelo_classifica_imagem
python step_classificacao_obra.py
```

Treina o Random Forest com pixels-semente de **todos** os `.tif` que encontrar em
`data/raw/imagens_satelite_landsat/` — nesse ponto, só os data centers de referência — e
classifica a série inteira de cada um numa tabela de % por classe/ano (sem gerar gráfico
nesse passo). Grava `ano_operacional_referencia` como coluna nos CSVs de saída (lido de
`data/silver/datacenters_referencia.csv` — ver `config_obra.REFERENCIA_CSV`), pra comparar
depois com a fase que o próximo passo detectar.

### Passo 4 — detectar as fases de obra

```bash
python deteccao_fases_obra.py
```

Fluxo separado (não toca em GeoTIFF/Earth Engine, só lê o CSV do passo 3) que decide, ano a
ano, se cada data center estava em Pré-obra / Início de obra / Durante obra / Fim de obra /
Pós-obra. Imprime a diferença entre o "Fim de obra" detectado e o `ano_operacional` real dos
data centers de referência — é essa diferença que você usa pra calibrar: se estiver grande,
ajuste os limiares no topo do próprio `deteccao_fases_obra.py` (não em `config_obra.py`) e
rode de novo — leva segundos, não precisa reclassificar imagem nenhuma.

Pra calibrar visualmente (não só pela tabela), tem um dashboard interativo publicado como
Claude Artifact — os limiares recalculam ao vivo e mostram o efeito direto nas imagens de
cada ano. É privado (só quem tem o link acessa); peça o link de quem rodou por último, já
que a URL muda a cada novo artifact publicado.

Saídas em `data/silver/cobertura_obra/`:
- `<nome>_cobertura_obra_por_ano.csv` (passo 3) e `cobertura_obra_todos_datacenters.csv`
  consolidado.
- `fases_obra_por_ano.csv` e `fases_obra_resumo_por_datacenter.csv` (passo 4).
- Overlays de conferência em `data/raw/imagens_satelite_landsat_overlay/`.

### Depois de calibrar

Ajustados os limiares (e, se precisar, apagado `data/models/rf_obra_landsat.joblib` pra
forçar retreino), troque pra base filtrada inteira em `extraction_landsat.py` (a linha já
comentada logo abaixo do CSV de referência) e rode os 4 passos de novo — dessa vez sem o
`_referencia` no passo 2, ou incluindo os dois se quiser continuar conferindo os casos
conhecidos separadamente.

## Teste paralelo: imagem menor (300m x 300m)

Existe uma segunda versão completa do pipeline (extração → JPG → treino/classificação →
fases), idêntica na lógica mas com a imagem capturada numa caixa de 300m x 300m em vez de
500m x 500m — serve pra comparar se reduzir o entorno capturado melhora a detecção nos sites
que pareciam "já urbanizados". Não sobrescreve nada do fluxo de 500m (saídas em pastas com
sufixo `_300m`, à parte). Ver docstring de `extraction_landsat_300m.py` pro raciocínio
completo.

```bash
python extraction_landsat_300m.py
python converte_tif_para_jpg_referencia_300m.py
cd ../../../modeling/modelo_classifica_imagem
python step_classificacao_obra_300m.py
python deteccao_fases_obra_300m.py
```

## Terceiro teste paralelo: Sentinel-2 em vez de Landsat

Existe também um fluxo inteiro à parte trocando o sensor (Sentinel-2, resolução nativa 10m
em vez de 30m) — ver [`extract/imagens_satelite/sentinel2/README.md`](../sentinel2/README.md).
Mesma amostra de referência, mesma lógica de classificação e de fases, saída em pastas
próprias — não toca em nada deste README nem dos scripts acima.

## Saídas (`data/raw/imagens_satelite_landsat/`)

- `<nome_datacenter>_<ano>.tif` — um GeoTIFF por (ponto, ano), bandas
  `SR_B2,SR_B3,SR_B4,SR_B5,SR_B6,SR_B7`.
- `<nome_datacenter>_metadata.json` — parâmetros da extração (`lat`, `lon`, `year_list`,
  `bands`, `buffer_m`, `scale`, `crs`).
- `data/raw/imagens_satelite_landsat_jpg/<nome_datacenter>_<ano>.jpg` — composição RGB, só
  pra inspeção visual.

## Arquivos

- `extracao_imagem_landsat.py` — funções reutilizáveis: extração, máscara de nuvem, RGB.
- `extraction_landsat.py` — script que de fato roda a extração pra um DataFrame de pontos
  (buffer de 250m → caixa de 500m x 500m).
- `converte_tif_para_jpg.py` / `converte_tif_para_jpg_referencia.py` — conversão TIF→JPG
  (lote inteiro vs. só a amostra de referência).
- `extraction_landsat_300m.py` / `converte_tif_para_jpg_referencia_300m.py` — mesma lógica dos
  dois acima, mas com buffer de 150m (→ caixa de 300m x 300m) e saída em pastas com sufixo
  `_300m`, pro teste paralelo comparativo (ver seção acima).

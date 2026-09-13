# modelo_classifica_imagem — classificação de cobertura do solo

Rotula, treina e classifica a série temporal de imagens de satélite baixada por
[`extract/imagens_satelite`](../../extract/imagens_satelite/README.md), transformando cada
GeoTIFF Sentinel-2 num % de área por classe de cobertura do solo. É a fonte das variáveis
de satélite (`prop_vegetacao_densa`, `prop_construida_urbana`, etc.) usadas em
[`modeling/modelo_impacto`](../modelo_impacto/README.md).

## Classes

| Classe | Cor | Origem no rótulo |
|---|---|---|
| Vegetação | verde | ESA WorldCover (classes 10,20,30,40,95,100) |
| Água | azul | ESA WorldCover (classes 80,90) |
| Construção | vermelho | ESA WorldCover (classe 50) |
| Estrada | cinza | malha viária OpenStreetMap (sobrepõe WorldCover) |
| Outro | amarelo | ESA WorldCover (classes 60,70 — solo exposto/outro) |

## Pipeline (por data center)

1. **Rótulo de referência** — exporta o [ESA WorldCover v200](https://esa-worldcover.org/)
   pro ano de `config.REFERENCE_YEAR` (padrão: 2024) na mesma região do GeoTIFF, remapeia
   pras 5 classes do projeto, e sobrepõe a malha viária do OpenStreetMap (via `osmnx`) —
   a classe "Estrada" tem prioridade sobre o que o WorldCover disser embaixo dela.
2. **Features** — cada pixel vira um vetor com as 6 bandas cruas do Sentinel-2 (`B2,B3,B4,
   B8,B11,B12`) + 9 índices espectrais (NDVI, NDWI, NDBI, EVI, SAVI, BSI, MNDWI, IBI, NDMI —
   ver `indices.py`).
3. **Treino** — amostra `config.N_SAMPLES_PER_CLASS` pixels por classe do rótulo do ano de
   referência e treina dois modelos: um Random Forest e uma rede neural densa (Keras).
4. **Classificação** — aplica os dois modelos em **todos** os anos disponíveis da série
   (`metadata.json` do Step 1), não só no ano de referência.
5. **Agregação** — calcula % de área e área em km² por classe/ano/modelo.

## Como rodar

```bash
cd data-extraction/modeling/modelo_classifica_imagem
pip install -r requirements.txt
python step2_classificacao_imagens.py                      # todos os data centers com metadata.json
python step2_classificacao_imagens.py --datacenter dc_123   # só um
```

Precisa de `EE_PROJECT` no `.env` da raiz (usado só pra exportar o rótulo WorldCover — a
classificação em si roda localmente, sem Earth Engine).

## Arquivos

- `classification.py` — funções reutilizáveis: exportar/remapear rótulos, treinar,
  classificar, agregar, plotar. Chamado pelo step, não roda sozinho.
- `indices.py` — cálculo dos índices espectrais (`load_features`). **Reconstruído durante a
  reorganização deste repositório** — o notebook original já importava esse módulo, mas o
  arquivo em si não estava entre o código migrado. As fórmulas usadas são as fórmulas padrão
  de sensoriamento remoto para cada índice; vale conferir se batem com o que foi de fato
  usado pra treinar os modelos já existentes antes de usar isso em produção (ver comentário
  no topo do arquivo).
- `step2_classificacao_imagens.py` — orquestra: acha todos os `*_metadata.json` em
  `data/raw/imagens_satelite/`, roda o pipeline pra cada data center, salva e consolida.

## Saídas

- `data/silver/cobertura_solo/<nome_datacenter>_cobertura_por_ano.csv` — % de área e área em
  km² por classe, ano e modelo (Random Forest / Rede Neural), um arquivo por data center.
- `data/silver/cobertura_solo/cobertura_todos_datacenters.csv` — os CSVs acima empilhados.
  É essa tabela que alimenta o painel consolidado de `modeling/modelo_impacto`.
- `data/silver/cobertura_solo/<nome_datacenter>_evolucao.png` — gráfico da evolução do % de
  área por classe ao longo dos anos (modelo Random Forest).
- `data/raw/imagens_satelite_overlay/<nome_datacenter>_<ano>_overlay.jpg` — composição RGB com
  a máscara de classificação sobreposta (semi-transparente), pra conferência visual de cada
  ano classificado.
- `data/raw/labels/<nome_datacenter>_worldcover.tif` — rótulo WorldCover exportado (cache
  intermediário, reaproveitável entre execuções).

## Variante: classificação de obra (vegetação densa / grama / solo exposto / construção)

`classification_obra.py` + `config_obra.py` + `step_classificacao_obra.py` são uma segunda
linha de classificação, separada da acima, que alimenta `deteccao_fases_obra.py` — um
terceiro fluxo, também separado, que decide a fase de obra (pré-obra / início / durante /
fim) a partir das % geradas — pra série temporal Landsat de
[`extract/imagens_satelite/landsat`](../../extract/imagens_satelite/landsat/README.md).

Diferença chave: aqui o rótulo de treino **não** vem só do WorldCover ou de limiar fixo.
Duas fontes de semente, combinadas:

1. **MapBiomas** (`labels_mapbiomas.py`, `config.USAR_MAPBIOMAS = True` por padrão) —
   classificação anual real do Brasil (não uma foto estática como o WorldCover), com classe
   própria de área urbana/solo exposto/floresta/pastagem. Cobre só até
   `labels_mapbiomas.ULTIMO_ANO_DISPONIVEL` (2024) — precisa de `PROJECT_ID` no `.env` pra
   exportar (mesma variável do `extraction_landsat.py`), cacheado em
   `data/raw/labels_mapbiomas/` depois da primeira vez.
2. **Limiares em índices espectrais** (NDVI/NDBI/BSI/SAVI/REDNESS) — usado onde o MapBiomas
   não opina (água, agricultura etc.) e nos anos fora da cobertura dele (2025/2026 na sua
   série). REDNESS `(R-G)/(R+G)` ajuda a não confundir solo exposto (avermelhado, óxido de
   ferro) com superfície clara/cinza que também tem BSI alto — mas não resolve telha
   cerâmica (também avermelhada) nem a variação de cor do solo por região do Brasil, por
   isso é só mais uma feature pro Random Forest, não uma regra isolada.

A zona cinzenta que sobra (pixels sem opinião de nenhuma das duas fontes) fica sem
rótulo-semente e é resolvida pelo Random Forest, treinado nos casos "óbvios" pooled de
**todos** os data centers/anos disponíveis — não um "ano de referência" por site.
`config.USAR_MAPBIOMAS = False` desliga a fonte 1 e treina só com a 2 (não precisa de Earth
Engine pra treinar nesse modo).

Passo a passo completo (extração → JPG → modelo, com amostra de referência de
`ano_operacional` conhecido pra calibrar os limiares) está no
[README do `extract/imagens_satelite/landsat`](../../extract/imagens_satelite/landsat/README.md#teste-inicial-com-amostra-de-referência).
Resumo de como rodar só esta parte, assumindo os GeoTIFFs já baixados:

```bash
cd data-extraction/modeling/modelo_classifica_imagem
python step_classificacao_obra.py       # treina + classifica -> % por classe/ano (sem gráfico)
python deteccao_fases_obra.py           # a partir das %, decide a fase de cada ano
```

`classification_obra.py` continua independente de `classification.py`/`indices.py` (que
puxam `osmnx` e `tensorflow`, não usados aqui). `labels_mapbiomas.py` é o único arquivo
dessa variante que precisa de `earthengine-api`/`geemap` — só é importado quando
`USAR_MAPBIOMAS=True`.

Saídas de `step_classificacao_obra.py` em `data/silver/cobertura_obra/` (mesmo formato do
pipeline principal, mas 4 classes, sem gráfico) e modelo treinado cacheado em
`data/models/rf_obra_landsat.joblib` (apague pra forçar retreino depois de ajustar os
limiares em `config_obra.py`). `deteccao_fases_obra.py` lê esse CSV e grava
`fases_obra_por_ano.csv` + `fases_obra_resumo_por_datacenter.csv` no mesmo diretório — seus
próprios limiares (% mínima por fase) ficam no topo do próprio arquivo, não em
`config_obra.py`, já que é um fluxo deliberadamente separado.

### `deteccao_fases_obra.py` — lógica de decisão

A classificação por ano não é puramente independente ano a ano (isso fragmentava demais —
ex.: um ano isolado voltando pra "Indefinido" entre dois anos de "Durante obra"), mas também
não olha a série inteira de uma vez de forma "global" — um protótipo de segmentação global
(tipo programação dinâmica) foi testado e **descartado**: ruído no fim da série conseguia
sobrescrever uma decisão correta no meio, quebrando a trava de "Pós-obra" (ver abaixo), que é
deliberadamente rígida. A versão em produção é um meio-termo, andando ano a ano com memória
de estado:

1. Classifica cada ano "cru" (`classifica_fase_ano`) a partir das % de cada classe naquele
   ano, mais `delta_solo` (variação de solo exposto vs. o ano observado anterior — ajuda a
   pegar "Início de obra" mesmo quando o solo exposto absoluto ainda está baixo, mas subiu
   rápido).
2. "Início de obra" só é confirmada se o ano seguinte mantiver ou avançar a fase (evita
   marcar início por causa de um ano ruidoso isolado); "Fim de obra" **não** passa por essa
   confirmação — fica imediata, porque atrasar essa detecção é pior que um falso positivo
   ocasional.
3. `preenche_buracos` fecha buracos de "Indefinido" cercados da mesma fase nos dois lados.
4. Uma vez atingido "Fim de obra", todo ano seguinte é travado em "Pós-obra" (não reavalia
   pra trás nem pra frente) — é essa trava que o approach de segmentação global quebrava.

`LIMIAR_CONSTRUCAO_FIM = 51` foi calibrado por grid search contra os 9 data centers de
referência (ver Calibrador de Obra abaixo). `LIMIAR_SOLO_EXPOSTO_FIM = 5` existe por causa de
sites sem margem de paisagismo visível (ex.: Ascenty Hortolândia HTL5, no pipeline de 300m):
"Fim de obra" também dispara se `solo_exposto` já está baixo, mesmo que `grama` nunca chegue
no limiar normal — sem essa condição OR, esses sites ficavam presos em "Durante obra"
indefinidamente.

### Dashboard de calibração (Claude Artifact)

Duas páginas interativas publicadas (privadas — só quem tem o link acessa), uma por pipeline,
com os 9 data centers de referência, imagens JPG de cada ano e sliders que recalculam os
limiares ao vivo:

- 500m: https://claude.ai/code/artifact/1485ddfe-daa1-418e-b52f-ed2728189a9f
- 300m: https://claude.ai/code/artifact/7d76b9d1-0b67-4ac4-8d72-9ec8fd96d836

Não são gerados por nenhum script do repo — foram montados manualmente a partir dos CSVs de
`fases_obra_por_ano.csv` + JPGs de cada ano. Se os CSVs mudarem (novo data center de
referência, limiares recalibrados), essas páginas precisam ser republicadas manualmente.

## Teste paralelo: imagem menor (300m)

`config_obra_300m.py`, `step_classificacao_obra_300m.py` e `deteccao_fases_obra_300m.py` são
cópias dos três arquivos equivalentes acima, apontando pra `data/raw/imagens_satelite_landsat_300m/`
em vez de `data/raw/imagens_satelite_landsat/` — mesmo raciocínio e mesmos limiares, servindo
só pra comparar contra a versão de 500m sem sobrescrever nada dela (ver
[README do `extract/imagens_satelite/landsat`](../../extract/imagens_satelite/landsat/README.md#teste-paralelo-imagem-menor-300m-x-300m)
pra como gerar os GeoTIFFs de entrada). `classification_obra.py` e `labels_mapbiomas.py` são
compartilhados entre as duas versões (não dependem do tamanho da caixa).

## Teste paralelo: Sentinel-2 em vez de Landsat

`config_obra_sentinel2.py`, `step_classificacao_obra_sentinel2.py` e
`deteccao_fases_obra_sentinel2.py` são a mesma ideia, mas trocando o sensor: apontam pra
`data/raw/imagens_satelite_sentinel2_obra/`, gerado por
[`extract/imagens_satelite/sentinel2`](../../extract/imagens_satelite/sentinel2/README.md).
Motivação: resolução nativa de 10m (vs 30m do Landsat) — numa caixa de mesmo tamanho (500m),
~9x mais pixel de textura por imagem, o que pode ajudar a separar o prédio do entorno já
urbanizado sem precisar encolher a caixa como no teste de 300m.

`classification_obra.py`/`labels_mapbiomas.py`/a lógica de `deteccao_fases_obra.py` são
100% compartilhadas com os fluxos Landsat — os índices são calculados por posição na pilha de
bandas (azul, verde, vermelho, NIR, SWIR1, SWIR2), e a ordem exportada pelo Sentinel-2
(`B2,B3,B4,B8,B11,B12`) já bate com essa convenção, sem adaptação nenhuma. Os limiares em
`config_obra_sentinel2.py`/`deteccao_fases_obra_sentinel2.py` começam iguais aos já
calibrados pro Landsat 500m, só como ponto de partida — a mistura de classe por pixel muda
bastante numa resolução tão mais fina, então recalibre antes de confiar nos resultados (ver
docstring de `deteccao_fases_obra_sentinel2.py`).

Ressalva: MapBiomas é nativo 30m — exportado na escala do Sentinel-2 (10m) pra alinhar
pixel a pixel com o resto do feature stack, cada pixel MapBiomas vira um bloco ~3x3 no
rótulo-semente (reamostragem, não um gabarito mais fino de verdade).

## Limitações conhecidas

- O treino usa só o ano de referência como rótulo — o WorldCover não tem uma versão
  histórica confiável pra todos os anos da série 2016-2026, então os demais anos são
  classificados com o modelo treinado num único ano (2024). Mudanças de cobertura muito
  anteriores a 2024 dependem do modelo generalizar bem, não de um rótulo daquele ano
  específico.
- `indices.py` foi reconstruído (ver acima) — mesma ressalva.

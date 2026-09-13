# modelo_grupo_controle — pareamento de grupo de controle

Acha, para cada data center do estudo, um **grupo de controle**: áreas
parecidas socioeconomicamente que não receberam data center, usadas depois em
`modeling/modelo_impacto/` como contrafactual (o que teria acontecido com
aquela região se o data center não tivesse sido construído — ver item 8 do
[guia de estrutura de dados](../modelo_impacto/guia_estrutura_dados_modelo_impacto.md)).

A ideia em duas etapas:

1. **Cidade similar** — para cada município do Brasil, acha o município mais
   parecido (mesmo perfil de população, PIB per capita e vocação econômica),
   dentro da mesma região do país.
2. **Pontos de controle** — mede a distância e a direção entre o centro do
   município do data center e o data center em si, e aplica essa mesma
   distância a partir do município similar, em 6 direções ao redor dele. Cada
   um desses 6 pontos vira um candidato a área de controle.

## Pipeline

| Step | Arquivo | Entrada | Saída |
|---|---|---|---|
| 1 | `step1_cidades_similares.py` | `data/raw/outputs_extraction/ibge_municipios.csv` | `data/silver/municipios_com_cidades_similares.csv` |
| 2 | `step2_grupo_controle.py` | `data/silver/datacenter_filtrado.csv` (de [`transform/filtra_datacenter`](../../transform/filtra_datacenter/README.md)) + saída do step1 | `data/silver/datacenter_expandido_6_pontos.csv` |
| — | `gerar_mapa_pontos_datacenter.py` | saída do step2 | `data/silver/mapa_datacenters.html` (conferência visual, não entra no pipeline) |

`nome_datacenter` (não tem mais `id_datacenter`) é o identificador usado em
todas as saídas abaixo — precisa ser único em `datacenter_filtrado.csv`.

Rodar em ordem (cada um lê o CSV que o anterior gerou):

```bash
cd data-extraction/modeling/modelo_grupo_controle
python step1_cidades_similares.py
python step2_grupo_controle.py
python gerar_mapa_pontos_datacenter.py   # opcional, só pra visualizar no navegador
```

## step1 — cidades similares

Agrupa os municípios por `regiao` (Norte/Nordeste/.../Sul) e roda um KNN
(distância euclidiana, features padronizadas em Z-Score) dentro de cada
grupo, usando o perfil médio 2016-2021 (`config.ANOS_ANALISE`) de:

- `populacao`, `pib_per_capita`
- `pct_va_servicos`, `pct_va_industria`, `pct_va_agropecuaria` (vocação econômica)
- `pct_impostos`

Salva, para cada município, os `config.N_SIMILARES` (padrão: 5) municípios
mais próximos, com um `percentual_similaridade` (`exp(-distância/2) * 100` —
100% = idêntico, cai exponencialmente com a distância Z-Score). Só o mais
próximo (`id_municipio_similar_1`) é usado no step2 hoje; os outros quatro
ficam disponíveis pra quando o pipeline passar a suportar múltiplos controles
por data center (ver item 8 do guia de estrutura de dados).

## step2 — grupo de controle (6 pontos)

Para cada data center filtrado:

1. Acha a cidade e o `id_municipio_similar_1` dela (do step1).
2. Calcula distância (Haversine) e azimute entre a sede do município e o
   data center — isto é, o quão longe e em que direção o data center fica do
   "centro" da sua cidade.
3. Aplica essa mesma distância a partir da sede do município similar, em
   `config.N_PONTOS_CONTROLE` (padrão: 6) direções espaçadas a cada 60°,
   começando no Norte (`config.INCLINACAO_INICIAL_GRAUS = 0`).

Cada um desses 6 pontos é uma linha no CSV de saída — candidatos a área de
controle a serem avaliados (visualmente, via mapa, e depois via nível/
tendência pré-obra) antes de decidir qual usar em `modelo_impacto/`.

## Por que 6 pontos e não 1

Um único ponto de controle correria o risco de cair em cima de outra
particularidade local (um rio, uma rodovia, um bairro já denso). Gerar 6
candidatos ao redor do mesmo município similar dá margem pra escolher o que
tiver nível/tendência pré-obra mais parecido com o do data center — essa
escolha final ainda é manual/visual (via `gerar_mapa_pontos_datacenter.py`),
não é feita automaticamente por nenhum desses steps.

## `data/silver/mapa_datacenters.html`

Mapa de satélite (Esri World Imagery) com, para cada data center: o marcador
do data center, o marcador da sede do município, o marcador do ponto de
controle escolhido e os 6 pontos de referência ao redor dele, cada um com o
quadrado de amostragem (`config.LADO_QUADRADO_KM`, padrão 3km x 3km) que será
efetivamente extraído do satélite em `extract/imagens_satelite/`. Serve só
pra conferência visual — não é lido por nenhum step seguinte.

# aneel_energia_municipio — estimativa de consumo de energia por município (ANEEL)

Estimativa de consumo de energia elétrica por **município e ano**, construída
a partir de dados abertos da ANEEL — já que **não existe, em lugar nenhum,
uma tabela pronta de consumo elétrico por município no Brasil** (nem na Base
dos Dados, nem na própria ANEEL — ver `extract/bigquery_mme_energia_uf/`
pro relatório dessa investigação, que só achou dado pronto em nível de UF).

## ⚠️ Isso é uma ESTIMATIVA, não uma medição

O SAMP da ANEEL (fonte de consumo) só existe em nível de **distribuidora**
(a empresa concessionária, cuja área de concessão cobre várias
municípios). Não tem como recuperar o consumo real de um município
específico a partir dele. O que esse pipeline faz é **ratear** o consumo
total de cada distribuidora entre os municípios da sua área de concessão,
**proporcionalmente à população** de cada um.

Isso é uma aproximação razoável pra comparar municípios de porte parecido,
mas **não captura variação real dentro da área de uma distribuidora** — um
polo industrial ou um data center novo num município pequeno vai consumir
muito mais energia do que sua população "merece" nesse rateio, e esse
excesso não aparece no resultado (ele fica escondido, dividido entre todos os
municípios da mesma distribuidora). Se o objetivo do estudo é justamente
detectar esse tipo de anomalia (ex.: impacto de data center na energia local),
**esse dataset não serve pra isso** — ele é útil como *baseline*/controle
agregado, não pra detectar consumo atípico de um município específico.

## Pipeline (3 steps, nessa ordem)

```bash
cd data-extraction/extract/aneel_energia_municipio
pip install -r requirements.txt
python step1_mapear_municipio_distribuidora.py
python step2_consumo_distribuidora_ano.py
python step3_rateio_energia_municipio.py
```

Não precisa de credencial nenhuma (dados abertos da ANEEL, sem autenticação) —
diferente das outras coletas de `extract/`, que usam BigQuery/Base dos Dados.

### Step 1 — `municipio -> distribuidora`

A ANEEL não publica esse vínculo diretamente. Construído combinando dois
datasets que não se falam:

- **IndQual Município** (`indqual-municipio`): município ↔ "conjunto de
  unidades consumidoras" (`IdeConjUnidConsumidoras`) — uma unidade geográfica
  interna da ANEEL, menor que a distribuidora.
- **Indicadores Coletivos de Continuidade — DEC/FEC**
  (`indicadores-coletivos-de-continuidade-dec-e-fec`): conjunto ↔
  distribuidora (`SigAgente`/`NumCNPJ`), usado aqui só pelo vínculo de
  identificação, não pelos indicadores de qualidade em si.

`município -> conjunto -> distribuidora` dá o vínculo que falta. Um
município pode ter mais de um conjunto associado (ou um conjunto pode trocar
de distribuidora ao longo do tempo, por fusão/privatização) — nesses casos,
fica com a distribuidora mais frequente entre os conjuntos do município
(maioria simples), pra garantir exatamente 1 distribuidora por município.

- **Saída:** `../../data/raw/outputs_extraction/aneel_municipio_distribuidora.csv`
- **Cobertura:** 5.568 de ~5.570 municípios (6 municípios do IndQual ficaram
  sem distribuidora encontrada — provavelmente conjuntos sem indicador de
  continuidade reportado em nenhuma das 3 décadas disponíveis).

### Step 2 — consumo por `distribuidora x ano`

Soma `VlrMercado` do SAMP (`samp-{ano}.parquet`, um arquivo por ano,
2003-presente) só nas combinações de campos que representam **energia de
fato consumida em kWh** (ver "Como o consumo é calculado" abaixo).

- **Saída:** `../../data/raw/outputs_extraction/aneel_consumo_distribuidora_ano.csv`

### Step 3 — rateio pra `município x ano`

```
consumo_estimado_município = consumo_distribuidora × (população_município / população_total_da_área_da_distribuidora)
```

População vem de `data/raw/outputs_extraction/ibge_municipios.csv`
(`extract/bigquery_ibge/`) — **precisa rodar aquela coleta antes** (ou já ter
o CSV). Como a série de população do IBGE ali começa em 2016, o resultado
final também começa em 2016, mesmo o SAMP/DEC-FEC cobrindo desde 2010/2003.

- **Saída:** `../../data/raw/outputs_extraction/aneel_energia_municipio.csv`
  — colunas: `id_municipio`, `municipio`, `uf`, `ano`, `sigla_distribuidora`,
  `cnpj_distribuidora`, `populacao`, `populacao_area_distribuidora`,
  `consumo_distribuidora_kwh` (total da distribuidora, sem ratear —
  útil pra conferência), `consumo_estimado_kwh` (o valor rateado, por município).

## Como o consumo é calculado (Step 2)

O SAMP guarda, na mesma coluna `VlrMercado`, dezenas de métricas diferentes
por linha — energia (kWh), demanda (kW), receita (R$), refaturamento de
meses anteriores, geração distribuída etc. — diferenciadas só pelas colunas
de texto `NomTipoMercado` / `DscOpcaoEnergia` / `DscDetalheMercado`. Somar
tudo sem filtrar conta a mesma energia várias vezes ou mistura R$ com kWh.

`config.COMBOS_ENERGIA_CONSUMIDA` usa:

| NomTipoMercado | DscOpcaoEnergia | DscDetalheMercado | O que é |
|---|---|---|---|
| `Regular` | `CATIVO` | `Energia TE (kWh)` | Energia faturada via Tarifa de Energia — consumidor cativo (compra da distribuidora local) |
| `Regular` | `LIVRE` | `Energia TUSD (kWh)` | Consumidor do mercado livre (compra de outro fornecedor) só paga TUSD à distribuidora local, mas o volume em kWh é o mesmo que ele efetivamente consumiu da rede |

Ficam de fora, deliberadamente:
- **`Refaturamento - Regular`** — readequação de meses anteriores; somar
  junto com `Regular` contaria a mesma energia duas vezes.
- **`Sistema de Compensação GD I`** (geração distribuída/net metering),
  **`Sistema Isolado`**, **`Sistema Individual`** — volumes bem menores,
  semântica mais ambígua (teria que decidir se conta energia bruta ou líquida
  da compensação), deixados fora pra manter a definição simples e auditável.
- Todas as linhas de receita (R$), demanda (kW), impostos, descontos etc.

Essa é uma escolha documentada, não a única correta — dá pra ajustar em
`config.COMBOS_ENERGIA_CONSUMIDA` se quiser incluir mais mercados (e ajustar
o filtro de `NomTipoMercado`/`DscDetalheMercado` de acordo).

## Fontes

- [SAMP](https://dadosabertos.aneel.gov.br/dataset/samp) — mercado de
  energia por distribuidora, mensal, 2003+.
- [IndQual Município](https://dadosabertos.aneel.gov.br/dataset/indqual-municipio)
  — vínculo município ↔ conjunto de unidades consumidoras.
- [Indicadores Coletivos de Continuidade (DEC/FEC)](https://dadosabertos.aneel.gov.br/dataset/indicadores-coletivos-de-continuidade-dec-e-fec)
  — usado só pelo vínculo conjunto ↔ distribuidora.

## Cache local

Os arquivos brutos baixados (SAMP e continuidade, em parquet) ficam em
`data/raw/aneel_cache/` e são reaproveitados entre execuções — apague essa
pasta se quiser forçar um redownload.

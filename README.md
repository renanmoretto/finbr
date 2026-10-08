# finbr

**CLI para dados do mercado financeiro brasileiro.** Ações, índices, macro (CDI/SELIC/IPCA), DI1, COTAHIST, notícias da B3 — direto do terminal.

```bash
$ finbr macro cdi
0.144

$ finbr acao PETR4
                            PETR4 — resumo
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ campo                ┃ valor                                     ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ nome                 │ PETROBRAS PN                              │
│ preco                │ 38.42                                     │
│ valor_de_mercado     │ 501,000,000,000                           │
│ ...                  │ ...                                       │
└──────────────────────┴───────────────────────────────────────────┘
```

## Instalação

**Recomendado** (instala `finbr` no PATH globalmente, isolado em venv próprio):

```bash
uv tool install git+https://github.com/renanmoretto/finbr
```

**Sem instalar** (execução efêmera):

```bash
uvx --from git+https://github.com/renanmoretto/finbr finbr macro cdi
```

**Pip clássico**:

```bash
pip install git+https://github.com/renanmoretto/finbr
```

## Visão geral dos comandos

```
finbr acao <ticker> [verbo]   — info, multiplos, dividendos, resultados, balanco, fluxo, precos, ...
finbr indice <nome> [verbo]   — precos, composicao
finbr macro <verbo>           — cdi, selic, ipca, serie, buscar, info
finbr di1 <ticker> <verbo>    — vencimento, dias, taxa, pu, dv01
finbr b3 cotahist <dia|ano>   — arquivos COTAHIST da B3
finbr b3 noticias             — plantão de notícias
finbr dus <verbo>             — calendário de dias úteis (B3)
finbr cache <verbo>           — info, limpar (cache em disco)
finbr screener                — screener de ações
```

Todo comando aceita `--help`. Por exemplo: `finbr acao --help`, `finbr macro ipca --help`.

## Formatos de saída

Por padrão, a CLI imprime **tabela colorida** quando rodando interativamente, e **CSV** quando a saída é piped/redirecionada — ou seja, "faz a coisa certa" automaticamente.

```bash
finbr macro buscar cdi                  # tabela bonita no terminal
finbr macro buscar cdi | head           # CSV, pronto pra pipe
finbr macro buscar cdi -f json | jq .   # JSON para jq
finbr macro ipca -o ipca.csv            # salva CSV
finbr b3 cotahist ano 2024 -o 2024.parquet # salva Parquet
```

Flags universais:

- `-f, --format {auto,table,json,csv,parquet}` — formato explícito.
- `-o, --output FILE` — salva em arquivo (formato inferido da extensão).

## Datas flexíveis

Onde for aceitar uma data, vale:

```
2024-01-15      # ISO
today, hoje
yesterday, ontem
-5d   -2w   -3m   -1y
```

Exemplos:

```bash
finbr acao PETR4 precos --since -1y
finbr b3 cotahist dia ontem
finbr macro ipca --since 2020-01-01
finbr dus delta today -n -5
```

## Cache

Downloads de COTAHIST e séries do SGS ficam em cache em disco, então repetir um comando é instantâneo.

```bash
finbr cache info                         # onde está e quanto ocupa
finbr cache limpar                       # apaga tudo
FINBR_NO_CACHE=1 finbr macro cdi         # ignora o cache nesta chamada
```

- Diretório: `~/.cache/finbr` (ou `$XDG_CACHE_HOME/finbr`; `FINBR_CACHE_DIR` sobrescreve).
- Validade: SGS 1h; COTAHIST de pregões e anos encerrados não expira; ano corrente 6h, dia corrente 1h.
- Vale também para o uso como biblioteca (`sgs.get`, `cotahist.get`, `cotahist.get_ano`).

## Exemplos

### Ações

```bash
finbr acao PETR4                         # resumo rápido (preço, MV, segmento, etc.)
finbr acao PETR4 multiplos               # múltiplos históricos
finbr acao PETR4 dividendos              # histórico de dividendos
finbr acao PETR4 dividendos --fonte fundamentus
finbr acao PETR4 resultados --periodo anual --ano-inicio 2018
finbr acao PETR4 balanco                 # balanço patrimonial
finbr acao PETR4 fluxo                   # fluxo de caixa
finbr acao PETR4 precos --since -1y      # preços do último ano (Yahoo)
```

### Índices

```bash
finbr indice IBOV                        # composição atual
finbr indice IBOV precos                 # série histórica completa
finbr indice SMLL precos --ano-inicio 2015 --ano-fim 2023
```

### Macro

```bash
finbr macro cdi                          # CDI ao ano
finbr macro cdi --diario                 # CDI diário
finbr macro selic
finbr macro ipca --since -5y             # IPCA mensal dos últimos 5 anos
finbr macro serie 12 --since 2024-01-01  # série SGS arbitrária
finbr macro buscar inflacao              # buscar séries SGS
finbr macro info 433                     # metadados da série
```

### DI1 (futuros)

```bash
finbr di1 DI1F26                         # default: data de vencimento
finbr di1 DI1F26 vencimento              # data de vencimento
finbr di1 DI1F26 dias                    # dias úteis até o vencimento
finbr di1 DI1F26 pu 0.12                 # preço unitário dado taxa
finbr di1 DI1F26 taxa 95000              # taxa dado PU
finbr di1 DI1F26 dv01 0.12               # DV01
```

### B3

```bash
finbr b3 cotahist dia 2024-10-15         # cotações de um pregão
finbr b3 cotahist ano 2024 -o 2024.parquet
finbr b3 noticias                        # plantão de hoje
finbr b3 noticias --since -7d --ticker PETR4
```

### Dias úteis

```bash
finbr dus proximo                        # próximo dia útil
finbr dus ultimo                         # dia útil anterior
finbr dus delta today -n -5              # 5 dias úteis atrás
finbr dus dif 2024-01-01 2024-06-01      # nº de dias úteis entre datas
finbr dus eh-util 2024-12-25             # "não"
finbr dus feriados 2024                  # feriados do ano
```

### Screener

```bash
finbr screener --limit 20                # 20 primeiras linhas
finbr screener -o screener.csv           # exporta tudo
```

## Como biblioteca Python

`finbr` também funciona como biblioteca — os mesmos dados em Python:

```python
import finbr

finbr.cdi()                              # 0.144
finbr.selic()
finbr.ipca()                             # pd.DataFrame

from finbr import sgs, dias_uteis
from finbr.b3 import di1, indices, cotahist, plantao_noticias
from finbr.statusinvest import acao
from finbr import fundamentus

sgs.get(12, data_inicio='2024-01-01')
indices.preco_historico('IBOV', ano_inicio=2020)
acao.detalhes('PETR4')
di1.taxa('DI1F26', preco_unitario=95000)
dias_uteis.proximo()
```

Tudo o que a CLI faz está disponível como função Python — a CLI é só um wrapper fino sobre os módulos. Os módulos exportados são os mesmos da v0.2.x, sem mudanças que quebrem código existente.

## Licença

MIT

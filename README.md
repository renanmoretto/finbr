# finbr

Coleção de utilitários Python para o mercado financeiro brasileiro.

`finbr` é um kit de ferramentas abrangente projetado para simplificar o trabalho com dados do mercado financeiro brasileiro. Ele fornece acesso fácil aos principais indicadores financeiros, preços de mercado e outros dados essenciais para análise e cálculos.

## Instalação

```bash
pip install finbr
```

## Exemplos de Uso

```python
import finbr

# Preços de Ativos
dados_precos = finbr.precos(['PETR4', 'VALE3'])

# CDI
# Retorna a taxa CDI anualizada recente, ex: 0.1415 (14.15%)
cdi_anual = finbr.cdi()
cdi_diario = finbr.cdi(ao_ano=False)  # taxa diária

# Taxa SELIC
# Retorna a taxa SELIC anualizada recente, ex: 0.1425 (14.25%)
selic_anual = finbr.selic()
selic_diaria = finbr.selic(ao_ano=False)  # taxa diária

# IPCA
taxa_ipca = finbr.ipca()
print(taxa_ipca)
# a saída é um pd.DataFrame
            ipca
data
1980-02-01  0.0462
1980-03-01  0.0604
1980-04-01  0.0529
1980-05-01  0.0570
1980-06-01  0.0531
...            ...
2024-10-01  0.0056
2024-11-01  0.0039
2024-12-01  0.0052
2025-01-01  0.0016
2025-02-01  0.0131
```

### `finbr.sgs` (SGS - Sistema Gerenciador de Séries Temporais do Banco Central)

O módulo `sgs` fornece acesso ao Sistema Gerenciador de Séries Temporais (SGS) do Banco Central do Brasil. Você pode encontrar mais informações aqui: https://www3.bcb.gov.br/sgspub/localizarseries/localizarSeries.do?method=prepararTelaLocalizarSeries

```python
from finbr import sgs

# série temporal por código. Retorna um pandas DataFrame.
serie_cdi = sgs.get(12)  # CDI
serie_ipca = sgs.get(433)  # IPCA

# múltiplas séries de uma vez
indicadores = sgs.get([12, 433, 189])  # CDI, IPCA, Selic

# séries com nomes personalizados
series_nomeadas = sgs.get({12: 'cdi', 433: 'ipca', 189: 'selic'})

# limitar por intervalo de datas
cdi_2020 = sgs.get(12, data_inicio='2020-01-01', data_fim='2020-12-31')

# pesquisar por séries
resultados = sgs.pesquisar("IPCA")

# metadados para uma série específica
metadados = sgs.metadata(433)
```

### `finbr.dias_uteis`

O módulo `dias_uteis` auxilia nos cálculos de dias úteis brasileiros, considerando feriados nacionais.

```python
from datetime import date
import finbr.dias_uteis as du

# verifica se uma data é um dia útil
eh_dia_util = du.dia_util(date(2023, 5, 1))  # False (Dia do Trabalho)

# obtém próximo dia útil
proximo_dia_util = du.proximo()  # Próximo dia útil a partir de hoje

# obtém dia útil anterior
dia_util_anterior = du.ultimo()  # Dia útil anterior a hoje

# adiciona ou subtrai dias úteis a uma data
data = date(2023, 1, 2)
data_futura = du.delta(data, 5)  # 5 dias úteis após 2 de janeiro
data_futura = du.delta(data, -5)  # 5 dias úteis antes de 2 de janeiro

# dias úteis entre duas datas
dias_uteis_intervalo = du.intervalo(date(2023, 1, 1), date(2023, 1, 31))

# todos os dias úteis em um ano
dias_uteis_do_ano = du.dias_uteis_ano(2023)

# todos os feriados em um ano
feriados_do_ano = du.feriados_ano(2023)

# calcula o número de dias úteis entre duas datas
diferenca_dias = du.dif(date(2023, 1, 1), date(2023, 1, 31))
```

### `finbr.b3`

O módulo `finbr.b3.di1` fornece ferramentas para trabalhar com os contratos futuros DI1 (Depósito Interfinanceiro) da B3.

```python
from finbr.b3 import di1

# verifica se um ticker é válido
di1.verifica_ticker('DI1F24')  # ticker válido, nenhuma exceção levantada
di1.verifica_ticker('DI1A24')  # ticker inválido, ValueError levantado

# obtém a data de vencimento de um contrato
di1.vencimento('DI1F24')  # retorna o primeiro dia útil de Jan 2024

# calcula o número de dias úteis ou corridos até o vencimento
di1.dias_vencimento('DI1F24')  # dias úteis até o vencimento
di1.dias_vencimento('DI1F24', dias_uteis=False)  # dias corridos

# calcula o preço unitário (PU) do contrato com base na taxa de juros
di1.preco_unitario('DI1F24', taxa=0.10)

# calcula a taxa de juros implícita a partir do preço
di1.taxa('DI1F24', preco_unitario=95000)

# calcula o DV01 (valor em reais de 1 ponto base)
di1.dv01('DI1F24', taxa=0.10)
```

O módulo `finbr.b3.indices` permite buscar preços históricos para índices da B3. Incluindo preços para o Índice IBOVESPA desde 1968.

```python
from finbr.b3 import indices

# retorna dados históricos do Ibovespa
ibov = indices.get('IBOV')

# outros índices com intervalo de anos específico
smll = indices.get('SMLL', ano_inicio=2015, ano_fim=2023)

# Índices disponíveis incluem:
# - IBOV (Ibovespa)
# - SMLL (Small Caps)
# - IDIV (Dividendos)
# E muitos outros
# Veja mais em https://www.b3.com.br/pt_br/market-data-e-indices/indices/indices-de-segmentos-e-setoriais/
```

O módulo `finbr.b3.cotahist` processa os arquivos de dados históricos COTAHIST da B3 contendo informações de negociação.

```python
from finbr.b3 import cotahist

# baixa dados para uma data específica
dados_diarios = cotahist.get('2023-05-15')

# baixa dados para um ano inteiro
dados_anuais = cotahist.get_ano(2022)

# leituras
dados_zip = cotahist.read_zip('caminho/para/COTAHIST_D20230515.ZIP') 
dados_txt = cotahist.read_txt('caminho/para/COTAHIST_D20230515.TXT')

# ou bytes
with open('caminho/para/arquivo.txt', 'rb') as f:
    dados_bytes = cotahist.read_bytes(f.read())
```

O módulo `finbr.b3.plantao_noticias` busca notícias corporativas do plantão de notícias da B3.
https://sistemasweb.b3.com.br/PlantaoNoticias/Noticias/Index

```python
from datetime import date
from finbr.b3 import plantao_noticias

# notícias de hoje
noticias_hoje = plantao_noticias.get()

# notícias a partir de uma data
noticias_data_especifica = plantao_noticias.get(inicio='2023-05-15')

# notícias para um intervalo de datas
noticias_intervalo_datas = plantao_noticias.get(inicio='2023-05-01', fim='2023-05-15')

# as notícias são um objeto NoticiaB3, com os seguintes atributos:
# informacoes, id_agencia, conteudo, data_hora, headline, titulo, id, empresa, ticker, ano, mes, dia, data, url
```

### `finbr.statusinvest` *(em desenvolvimento)*

O módulo `statusinvest.acao` permite buscar informações de ações do site StatusInvest (https://statusinvest.com.br/).
PS: a saída dos dados é uma lista de dicionários

```python
from finbr.statusinvest import acao

detalhes_empresa = acao.detalhes('PETR4')
print(f"Empresa: {detalhes_empresa['nome']}")
print(f"CNPJ: {detalhes_empresa['cnpj']}")
print(f"Valor de Mercado: {detalhes_empresa['valor_de_mercado']}")

resultados_trimestrais = acao.resultados('PETR4') # padrão trimestral
resultados_anuais = acao.resultados('PETR4', periodo='anual')
resultados_intervalo = acao.resultados('PETR4', ano_inicio=2018, ano_fim=2022)

balanco_trimestral = acao.balanco('PETR4')
balanco_anual = acao.balanco('PETR4', periodo='anual')

dados_fluxo_caixa = acao.fluxo_de_caixa('PETR4')

dados_multiplos = acao.multiplos('PETR4')

historico_dividendos = acao.dividendos('PETR4')

historico_payout = acao.payouts('PETR4')

# dataframe com o screener de todas as ações
todas_acoes = acao.screener()
```

TODOs: FIIs, Ações, Fundos

### `finbr.fundamentus` *(em desenvolvimento)*

O módulo `fundamentus` permite buscar informações de ações do site Fundamentus (https://fundamentus.com.br/).

```python
from finbr import fundamentus

detalhes_empresa = fundamentus.detalhes('PETR4')
print(f"P/L: {detalhes_empresa['p_l']}")
print(f"ROE: {detalhes_empresa['roe']}")
print(f"Valor de Mercado: {detalhes_empresa['valor_de_mercado']}")

dividendos = fundamentus.proventos('PETR4')

trimestrais = fundamentus.resultados_trimestrais('PETR4')

apresentacoes = fundamentus.apresentacoes('PETR4')
```

## Licença

MIT
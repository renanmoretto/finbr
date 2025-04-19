import io
import json
import base64
import datetime
from functools import lru_cache

import pandas as pd
import requests


def _transform_index_data(df_raw: pd.DataFrame, year: int) -> dict[datetime.date, float]:
    months = {
        'Jan': 1,
        'Fev': 2,
        'Mar': 3,
        'Abr': 4,
        'Mai': 5,
        'Jun': 6,
        'Jul': 7,
        'Ago': 8,
        'Set': 9,
        'Out': 10,
        'Nov': 11,
        'Dez': 12,
    }

    prices = {}

    for month in months:
        month_i = months[month]
        month_df = df_raw[month]
        for date, str_v in month_df.to_dict().items():
            if pd.isna(str_v):
                continue
            if isinstance(str_v, str):
                v = float(str_v.replace('.', '').replace(',', '.'))
            else:
                v = str_v
            date = datetime.date(year, month_i, int(date))
            prices[date] = v
    return prices


@lru_cache(maxsize=1000)
def _get_data(index: str, year: int) -> dict[datetime.date, float]:
    _dic = {'index': index, 'language': 'pt-br', 'year': str(year)}

    b64_string = base64.b64encode(json.dumps(_dic, separators=(',', ':')).encode()).decode()
    url = f'https://sistemaswebb3-listados.b3.com.br/indexStatisticsProxy/IndexCall/GetDownloadPortfolioDay/{b64_string}'
    r = requests.get(url)

    if r.content == b'':
        raise ValueError(f'não há dados para {year}')

    df_raw = pd.read_csv(
        io.BytesIO(base64.b64decode(r.content)), sep=';', encoding='latin1', skiprows=1, decimal=','
    )
    df_raw = df_raw.query('Dia not in ["MÍNIMO", "MÍNIMO", "MÁXIMO"]')
    df_raw = df_raw.set_index('Dia')

    return _transform_index_data(df_raw, year)


@lru_cache(maxsize=100)
def _get_index_first_year(index: str) -> int:
    data = {
        'pageNumber': 1,
        'pageSize': 100,
        'index': index,
        'language': 'pt-br',
        'year': 1950,
        'yearEnd': 2025,
    }

    b64_string = base64.b64encode(json.dumps(data, separators=(',', ':')).encode()).decode()
    url = f'https://sistemaswebb3-listados.b3.com.br/indexStatisticsProxy/IndexCall/GetYearlyVariation/{b64_string}'
    r = requests.get(url)
    r_json = r.json()
    results = r_json['results']
    if not results:
        raise ValueError(f"não há dados para o índice '{index}'")
    index_first_year = results[-1]['year']
    return int(index_first_year)


def get(
    indice: str,
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> pd.DataFrame:
    """
    Faz o download dos dados históricos de preços para um índice da B3.

    Esta função busca dados históricos de preços para um índice B3 especificado (como IBOV, SMLL, IDIV)
    para o intervalo de anos fornecido. Se nenhum intervalo for especificado, buscará todos os dados disponíveis.

    Parâmetros
    ----------
    indice : str
        O código do índice (ex.: 'IBOV' para Ibovespa, 'SMLL' para Small Caps, 'IDIV' para Dividendos, etc).
    ano_inicio : int, opcional
        O primeiro ano a ser incluído nos dados. Se None, começa do primeiro ano disponível.
    ano_fim : int, opcional
        O último ano a ser incluído nos dados. Se None, termina no ano atual.

    Retorno
    -------
    pd.DataFrame
        Um DataFrame contendo os dados históricos de preços com datas como índice e os valores do índice
        em uma coluna nomeada conforme o índice (em minúsculo).

    Exemplos
    --------
    >>> ibov = get('IBOV')
    >>> ibov_2020 = get('IBOV', ano_inicio=2020)
    >>> small_caps = get('SMLL', ano_inicio=2015, ano_fim=2023)
    """
    if ano_fim is None:
        ano_fim = datetime.date.today().year + 1

    if ano_inicio is None:
        ano_inicio = _get_index_first_year(indice)

    data = {}
    for year in range(ano_inicio, ano_fim):
        try:
            year_data = _get_data(indice, year)
            data.update(year_data)
        except ValueError:
            continue

    df = pd.Series(data).to_frame()
    df.index = pd.to_datetime(df.index)
    df.index.name = 'date'
    df.columns = [indice.lower()]
    return df

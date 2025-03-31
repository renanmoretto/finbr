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
        raise ValueError(f'no data for {year}')

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
        raise ValueError(f"no data for index '{index}'")
    index_first_year = results[-1]['year']
    return int(index_first_year)


def get(
    index: str,
    start_year: int | None = None,
    end_year: int | None = None,
) -> pd.DataFrame:
    """
    Retrieve historical price data for a B3 index.

    This function fetches historical price data for a specified B3 index (such as IBOV, SMLL, IDIV)
    for the given year range. If no range is specified, it will fetch all available data from the
    first year the index was available up to the current year.

    Parameters
    ----------
    index : str
        The index code (e.g., 'IBOV' for Ibovespa, 'SMLL' for Small Caps, 'IDIV' for Dividends, etc).
    start_year : int, optional
        The first year to include in the data. If None, starts from the first available year.
    end_year : int, optional
        The last year to include in the data. If None, ends at the current year.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the historical price data with dates as index and the index values
        as a column named after the index (lowercase).

    Examples
    --------
    >>> ibov = get('IBOV')
    >>> ibov_recent = get('IBOV', start_year=2020)
    >>> small_caps = get('SMLL', start_year=2015, end_year=2023)
    """
    if end_year is None:
        end_year = datetime.date.today().year + 1

    if start_year is None:
        start_year = _get_index_first_year(index)

    data = {}
    for year in range(start_year, end_year):
        try:
            year_data = _get_data(index, year)
            data.update(year_data)
        except ValueError:
            continue

    df = pd.Series(data).to_frame()
    df.index = pd.to_datetime(df.index)
    df.index.name = 'date'
    df.columns = [index.lower()]
    return df

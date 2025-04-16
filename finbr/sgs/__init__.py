import datetime
import time
from typing import Generator

import requests
from requests.exceptions import ReadTimeout
import pandas as pd
import polars as pl
from bs4 import BeautifulSoup


_URL = 'https://api.bcb.gov.br'
_URL_SGS_PUB = 'https://www3.bcb.gov.br/sgspub/'
DEFAULT_TIMEOUT = 20


def _make_chunks(
    start: datetime.date | None = None,
    end: datetime.date | None = None,
    chunk_size: int = 360 * 10,
) -> Generator[tuple[datetime.date, datetime.date], None, None]:
    """chunk_size is in number of days"""
    start = start or datetime.date(1900, 1, 1)
    end = end or datetime.date.today()

    # check if range fits chunk size
    date_range = end - start
    if date_range.days <= chunk_size:
        yield start, end
        return

    chunk_start = end - datetime.timedelta(days=chunk_size)
    chunk_end = end
    while chunk_start >= start:
        yield chunk_start, chunk_end
        chunk_end = chunk_start - datetime.timedelta(days=1)
        chunk_start = chunk_start - datetime.timedelta(days=chunk_size)

    yield start, chunk_end


def _get_data_in_chunks(
    code: int,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
    timeout: int = DEFAULT_TIMEOUT,  # lower than 20 will cause timeout errors, sgs api sometimes is slow
    session: requests.Session | None = None,
) -> list[dict]:
    def _safe_get(url, session, timeout=DEFAULT_TIMEOUT, retries=3, backoff=2):
        for i in range(retries):
            try:
                return session.get(url, timeout=timeout)
            except ReadTimeout:
                time.sleep(backoff**i)
        raise ReadTimeout(f'Failed to get {url} after {retries} retries')

    if session is None:
        session = requests.Session()

    data = []
    for chunk_start, chunk_end in _make_chunks(start, end):
        url = f'{_URL}/dados/serie/bcdata.sgs.{code}/dados?formato=json&dataInicial={chunk_start:%d/%m/%Y}&dataFinal={chunk_end:%d/%m/%Y}'

        # sometimes sgs api is slow to respond, so we need to retry
        # but after the first try, it will be faster
        response = _safe_get(url, session, timeout=timeout)

        if response.status_code == 404:  # 404 means the series is not found, so we can break
            break

        if response.status_code != 200:
            raise requests.HTTPError(f'Status code {response.status_code}: {response.text}')

        sgs_data = response.json()
        data.extend(sgs_data)

    session.close()

    # sort data by date
    sorted_data = (
        pl.DataFrame(data)
        .with_columns(data_dt=pl.col('data').str.strptime(pl.Datetime, '%d/%m/%Y'))
        .sort('data_dt')
        .drop('data_dt')
        .to_dicts()
    )

    return sorted_data


def _get_raw_data(
    code: int,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    session: requests.Session | None = None,
) -> list[dict]:
    start_str = start.strftime('%d/%m/%Y') if start else ''
    end_str = end.strftime('%d/%m/%Y') if end else ''

    url = f'{_URL}/dados/serie/bcdata.sgs.{code}/dados?formato=json&dataInicial={start_str}&dataFinal={end_str}'

    if session is None:
        response = requests.get(url, timeout=timeout)
    else:
        response = session.get(url, timeout=timeout)

    if response.status_code != 200:
        raise requests.HTTPError(f'Status code {response.status_code}: {response.text}')

    response_json = response.json()

    if isinstance(response_json, list):
        return response_json

    if isinstance(response_json, dict):
        if (
            'error' in response_json.keys()
            and response_json['error']
            == 'O sistema aceita uma janela de consulta de, no máximo, 10 anos em séries de periodicidade diária'
        ):
            return _get_data_in_chunks(code, start, end, timeout, session)

    raise ValueError(f'Unexpected response format: {response_json}')


def _get_data(
    code: int,
    start: datetime.date | None = None,
    end: datetime.date | None = None,
    rename_to: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    session: requests.Session | None = None,
) -> pd.Series:
    data = _get_raw_data(code, start, end, timeout, session)
    values = [v['valor'] for v in data]
    s = pd.Series(
        pd.to_numeric(values),
        index=pd.to_datetime([v['data'] for v in data], format='%d/%m/%Y'),
    )
    s.index.name = 'data'
    s.name = rename_to or code
    return s


def get(
    code: int | list[int] | dict[int, str],
    start: datetime.date | str | None = None,
    end: datetime.date | str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> pd.DataFrame:
    """Fetch one or multiple time series from the Brazilian Central Bank's SGS as a DataFrame.

    Parameters
    ----------
    code : int or list or dict
        If int, fetches a single series.
        If list, fetches multiple series using the codes in the list.
        If dict, fetches series using codes as keys and uses the values as column names.
    start : datetime.date or str, optional
        Start date for the series data. If string, must be in 'YYYY-MM-DD' format.
        If None, fetches from the earliest available date.
    end : datetime.date or str, optional
        End date for the series data. If string, must be in 'YYYY-MM-DD' format.
        If None, fetches until the latest available date.
    timeout : int, default 20
        Timeout for the request.
        NOTE: We recomend using high timeouts for daily series. SGS API can be slow at times.

    Returns
    -------
    pandas.DataFrame
        A DataFrame with dates as index and series values as columns.
        Column names will be the integer codes or the specified names for dict input.

    Examples
    --------
    >>> sgs.get(12)  # Single series
    >>> sgs.get([12, 433])  # Multiple series
    >>> sgs.get({12: 'cdi', 433: 'poupanca'})  # Multiple series with custom names
    >>> sgs.get(12, start='2020-01-01')  # From specific start date
    >>> sgs.get(12, start='2015-01-01', end='2020-01-01')  # Date range
    """
    if isinstance(start, str):
        start = datetime.datetime.strptime(start, '%Y-%m-%d').date()
    if isinstance(end, str):
        end = datetime.datetime.strptime(end, '%Y-%m-%d').date()

    if isinstance(code, int):
        data = _get_data(code, start, end, timeout=timeout)

    # on list and dicts, use a session to avoid cookies issues and speed up requests
    elif isinstance(code, list):
        with requests.Session() as session:
            data = pd.DataFrame()
            for c in code:
                single_data = _get_data(
                    c,
                    start,
                    end,
                    timeout=timeout,
                    session=session,
                )
                data = pd.concat([data, single_data], axis=1)

    elif isinstance(code, dict):
        with requests.Session() as session:
            data = pd.DataFrame()
            for c, name in code.items():
                single_data = _get_data(
                    c,
                    start,
                    end,
                    rename_to=name,
                    timeout=timeout,
                    session=session,
                )
                data = pd.concat([data, single_data], axis=1)

    data.index = pd.to_datetime(data.index)
    data.index.name = 'date'

    if isinstance(data, pd.Series):
        return pd.DataFrame(data)
    return data


# search/metadata


def _search(query: int | str, language: str = 'pt') -> requests.Response:
    url = f'{_URL_SGS_PUB}/localizarseries/localizarSeries.do'

    params = {
        'method': 'localizarSeriesPorCodigo'
        if isinstance(query, int)
        else 'localizarSeriesPorTexto',
        'periodicidade': 0,
        'codigo': query if isinstance(query, int) else None,
        'fonte': 341,
        'texto': query if isinstance(query, str) else None,
        'hdFiltro': None,
        'hdOidGrupoSelecionado': None,
        'hdSeqGrupoSelecionado': None,
        'hdNomeGrupoSelecionado': None,
        'hdTipoPesquisa': 4 if isinstance(query, int) else 6,
        'hdTipoOrdenacao': 0,
        'hdNumPagina': None,
        'hdPeriodicidade': 'Todas',
        'hdSeriesMarcadas': None,
        'hdMarcarTodos': None,
        'hdFonte': None,
        'hdOidSerieMetadados': None,
        'hdNumeracao': None,
        'hdOidSeriesLocalizadas': None,
        'linkRetorno': '/sgspub/consultarvalores/telaCvsSelecionarSeries.paint',
        'linkCriarFiltros': '/sgspub/manterfiltros/telaMfsCriarFiltro.paint',
    }
    with requests.Session() as session:
        # get cookies
        session.get(f'{_URL_SGS_PUB}/', timeout=DEFAULT_TIMEOUT)

        response = session.post(url, params=params, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return response


def _parse_metadata_data(r: requests.Response) -> list[dict]:
    soup = BeautifulSoup(r.text, 'html.parser')
    table = soup.find('table', id='tabelaSeries')
    series_data = []
    if table:
        rows = table.find_all('tr')[1:]  # type: ignore
        for row in rows:
            cols = row.find_all('td')  # type: ignore
            if cols:
                series = {
                    'code': cols[1].text.strip(),
                    'name': cols[2].text.strip(),
                    'unit': cols[3].text.strip(),
                    'frequency': cols[4].text.strip(),
                    'start_date': cols[5].text.strip(),
                    'end_date': cols[6].text.strip(),
                    'source_name': cols[7].text.strip(),
                    'special': cols[8].text.strip(),
                }
                series_data.append(series)
    return series_data


def search(query: int | str, language: str = 'pt') -> list[dict]:
    """Search for time series in the Brazilian Central Bank's SGS by code or keyword.

    Parameters
    ----------
    query : int or str
        If int, searches for a specific series code.
        If str, searches for series containing the keyword in their name.
    language : str, default "pt"
        Language for search interface and results. Options are "pt" for Portuguese or "en" for English.

    Returns
    -------
    List[Dict]
        A list of dictionaries where each dictionary contains metadata about a matching series.
        Each dictionary includes: code, name, unit, frequency, start_date, end_date, source_name, and special.

    Examples
    --------
    >>> sgs.search("cdi")  # Search by keyword
    >>> sgs.search(12)  # Search by code
    >>> sgs.search("inflation", language="en")  # Search in English
    """
    r = _search(query, language)
    return _parse_metadata_data(r)


def metadata(code: int, language: str = 'pt') -> dict:
    """Fetch metadata about a specific time series from the Brazilian Central Bank's SGS.

    Parameters
    ----------
    code : int
        The code of the series to fetch metadata for.
    language : str, default "pt"
        Language for the metadata results. Options are "pt" for Portuguese or "en" for English.

    Returns
    -------
    Dict
        A dictionary containing metadata about the series, including:
        code, name, unit, frequency, start_date, end_date, source_name, and special.

    Examples
    --------
    >>> sgs.metadata(12)  # Get metadata for CDI series
    >>> sgs.metadata(433, language="en")  # Get metadata for IPCA series in English
    """
    r = _search(code, language)
    return _parse_metadata_data(r)[0]

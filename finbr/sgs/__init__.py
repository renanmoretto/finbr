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
    inicio: datetime.date | None = None,
    fim: datetime.date | None = None,
    chunk_size: int = 360 * 10,
) -> Generator[tuple[datetime.date, datetime.date], None, None]:
    """chunk_size is in number of days"""
    inicio = inicio or datetime.date(1900, 1, 1)
    fim = fim or datetime.date.today()

    # check if range fits chunk size
    date_range = fim - inicio
    if date_range.days <= chunk_size:
        yield inicio, fim
        return

    chunk_inicio = fim - datetime.timedelta(days=chunk_size)
    chunk_fim = fim
    while chunk_inicio >= inicio:
        yield chunk_inicio, chunk_fim
        chunk_fim = chunk_inicio - datetime.timedelta(days=1)
        chunk_inicio = chunk_inicio - datetime.timedelta(days=chunk_size)

    yield inicio, chunk_fim


def _get_data_in_chunks(
    codigo: int,
    inicio: datetime.date | None = None,
    fim: datetime.date | None = None,
    timeout: int = DEFAULT_TIMEOUT,
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
    for chunk_inicio, chunk_fim in _make_chunks(inicio, fim):
        url = f'{_URL}/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={chunk_inicio:%d/%m/%Y}&dataFinal={chunk_fim:%d/%m/%Y}'

        # às vezes a API do sgs é lenta para responder, então precisamos tentar novamente
        # mas após a primeira tentativa, geralmente será mais rápido
        response = _safe_get(url, session, timeout=timeout)

        if (
            response.status_code == 404
        ):  # 404 significa que a série não foi encontrada, então podemos interromper
            break

        if response.status_code != 200:
            raise requests.HTTPError(f'Status code {response.status_code}: {response.text}')

        sgs_data = response.json()
        data.extend(sgs_data)

    session.close()

    # ordena os dados pela data
    sorted_data = (
        pl.DataFrame(data)
        .with_columns(data_dt=pl.col('data').str.strptime(pl.Datetime, '%d/%m/%Y'))
        .sort('data_dt')
        .drop('data_dt')
        .to_dicts()
    )

    return sorted_data


def _get_raw_data(
    codigo: int,
    inicio: datetime.date | None = None,
    fim: datetime.date | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    session: requests.Session | None = None,
) -> list[dict]:
    inicio_str = inicio.strftime('%d/%m/%Y') if inicio else ''
    fim_str = fim.strftime('%d/%m/%Y') if fim else ''

    url = f'{_URL}/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={inicio_str}&dataFinal={fim_str}'

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
            return _get_data_in_chunks(codigo, inicio, fim, timeout, session)

    raise ValueError(f'Unexpected response format: {response_json}')


def _get_data(
    codigo: int,
    inicio: datetime.date | None = None,
    fim: datetime.date | None = None,
    renomear_para: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    session: requests.Session | None = None,
) -> pd.Series:
    data = _get_raw_data(codigo, inicio, fim, timeout, session)
    valores = [v['valor'] for v in data]
    s = pd.Series(
        pd.to_numeric(valores),
        index=pd.to_datetime([v['data'] for v in data], format='%d/%m/%Y'),
    )
    s.index.name = 'data'
    s.name = renomear_para or codigo
    return s


def get(
    codigo: int | list[int] | dict[int, str],
    inicio: datetime.date | str | None = None,
    fim: datetime.date | str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> pd.DataFrame:
    """Fetch one or multiple time series from the Brazilian Central Bank's SGS as a DataFrame.

    Parameters
    ----------
    codigo : int or list or dict
        If int, fetches a single series.
        If list, fetches multiple series using the codes in the list.
        If dict, fetches series using codes as keys and uses the values as column names.
    inicio : datetime.date or str, optional
        Start date for the series data. If string, must be in 'YYYY-MM-DD' format.
        If None, fetches from the earliest available date.
    fim : datetime.date or str, optional
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
    if isinstance(inicio, str):
        inicio = datetime.datetime.strptime(inicio, '%Y-%m-%d').date()
    if isinstance(fim, str):
        fim = datetime.datetime.strptime(fim, '%Y-%m-%d').date()

    if isinstance(codigo, int):
        data = _get_data(codigo, inicio, fim, timeout=timeout)

    # on list and dicts, use a session to avoid cookies issues and speed up requests
    elif isinstance(codigo, list):
        with requests.Session() as session:
            data = pd.DataFrame()
            for c in codigo:
                single_data = _get_data(
                    c,
                    inicio,
                    fim,
                    timeout=timeout,
                    session=session,
                )
                data = pd.concat([data, single_data], axis=1)

    elif isinstance(codigo, dict):
        with requests.Session() as session:
            data = pd.DataFrame()
            for c, nome in codigo.items():
                single_data = _get_data(
                    c,
                    inicio,
                    fim,
                    renomear_para=nome,
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


def _search(query: int | str, idioma: str = 'pt') -> requests.Response:
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


def _parse_metadata(r: requests.Response) -> list[dict]:
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


def pesquisar(query: int | str, idioma: str = 'pt') -> list[dict]:
    """Search for time series in the Brazilian Central Bank's SGS by code or keyword.

    Parameters
    ----------
    query : int or str
        If int, searches for a specific series code.
        If str, searches for series containing the keyword in their name.
    idioma : str, default "pt"
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
    >>> sgs.search("inflation", idioma="en")  # Search in English
    """
    r = _search(query, idioma)
    return _parse_metadata(r)


def metadata(codigo: int, idioma: str = 'pt') -> dict:
    """Fetch metadata about a specific time series from the Brazilian Central Bank's SGS.

    Parameters
    ----------
    codigo : int
        The codigo of the series to fetch metadata for.
    idioma : str, default "pt"
        Language for the metadata results. Options are "pt" for Portuguese or "en" for English.

    Returns
    -------
    Dict
        A dictionary containing metadata about the series, including:
        codigo, name, unit, frequency, start_date, end_date, source_name, and special.

    Examples
    --------
    >>> sgs.metadata(12)  # Get metadata for CDI series
    >>> sgs.metadata(433, idioma="en")  # Get metadata for IPCA series in English
    """
    r = _search(codigo, idioma)
    return _parse_metadata(r)[0]

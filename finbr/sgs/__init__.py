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
        raise ReadTimeout(f'Falha ao obter {url} após {retries} tentativas')

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

    raise ValueError(f'Formato de resposta inesperado: {response_json}')


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
    data_inicio: datetime.date | str | None = None,
    data_fim: datetime.date | str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> pd.DataFrame:
    """Busca uma ou múltiplas séries temporais do SGS do Banco Central do Brasil como um DataFrame.

    Parâmetros
    ----------
    codigo : int ou list ou dict
        Se int, busca uma única série.
        Se list, busca múltiplas séries usando os códigos na lista.
        Se dict, busca séries usando os códigos como chaves e usa os valores como nomes das colunas.
    data_inicio : datetime.date ou str, opcional
        Data inicial para os dados da série. Se string, deve estar no formato 'YYYY-MM-DD'.
        Se None, busca desde a data mais antiga disponível.
    data_fim : datetime.date ou str, opcional
        Data final para os dados da série. Se string, deve estar no formato 'YYYY-MM-DD'.
        Se None, busca até a data mais recente disponível.
    timeout : int, padrão 20
        Timeout para a requisição.
        NOTA: Recomendamos usar timeouts altos para séries diárias. A API do SGS pode ser lenta às vezes.

    Retorno
    -------
    pandas.DataFrame
        Um DataFrame com datas como índice e valores das séries como colunas.
        Os nomes das colunas serão os códigos inteiros ou os nomes especificados para entrada do tipo dict.

    Exemplos
    --------
    >>> sgs.get(12)  # Série única
    >>> sgs.get([12, 433])  # Múltiplas séries
    >>> sgs.get({12: 'cdi', 433: 'poupanca'})  # Múltiplas séries com nomes customizados
    >>> sgs.get(12, start='2020-01-01')  # A partir de uma data específica
    >>> sgs.get(12, start='2015-01-01', end='2020-01-01')  # Intervalo de datas
    """
    if isinstance(data_inicio, str):
        data_inicio = datetime.datetime.strptime(data_inicio, '%Y-%m-%d').date()
    if isinstance(data_fim, str):
        data_fim = datetime.datetime.strptime(data_fim, '%Y-%m-%d').date()

    if isinstance(codigo, int):
        data = _get_data(codigo, data_inicio, data_fim, timeout=timeout)

    # on list and dicts, use a session to avoid cookies issues and speed up requests
    elif isinstance(codigo, list):
        with requests.Session() as session:
            data = pd.DataFrame()
            for c in codigo:
                single_data = _get_data(
                    c,
                    data_inicio,
                    data_fim,
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
                    data_inicio,
                    data_fim,
                    renomear_para=nome,
                    timeout=timeout,
                    session=session,
                )
                data = pd.concat([data, single_data], axis=1)

    data.index = pd.to_datetime(data.index)
    data.index.name = 'data'

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
    """Busca séries temporais no SGS do Banco Central do Brasil por código ou palavra-chave.

    Parâmetros
    ----------
    query : int ou str
        Se int, busca por um código de série específico.
        Se str, busca por séries que contenham a palavra-chave no nome.
    idioma : str, padrão "pt"
        Idioma da interface de busca e dos resultados. Opções são "pt" para português ou "en" para inglês.

    Retorno
    -------
    List[Dict]
        Uma lista de dicionários, onde cada dicionário contém metadados sobre uma série encontrada.
        Cada dicionário inclui: code, name, unit, frequency, start_date, end_date, source_name e special.

    Exemplos
    --------
    >>> sgs.search("cdi")  # Busca por palavra-chave
    >>> sgs.search(12)  # Busca por código
    >>> sgs.search("inflation", idioma="en")  # Busca em inglês
    """
    r = _search(query, idioma)
    return _parse_metadata(r)


def metadata(codigo: int, idioma: str = 'pt') -> dict:
    """Busca metadados sobre uma série temporal específica do SGS do Banco Central do Brasil.

    Parâmetros
    ----------
    codigo : int
        O código da série para buscar os metadados.
    idioma : str, padrão "pt"
        Idioma dos resultados dos metadados. Opções são "pt" para português ou "en" para inglês.

    Retorno
    -------
    Dict
        Um dicionário contendo metadados sobre a série, incluindo:
        codigo, name, unit, frequency, start_date, end_date, source_name e special.

    Exemplos
    --------
    >>> sgs.metadata(12)  # Metadados da série CDI
    >>> sgs.metadata(433, idioma="en")  # Metadados da série IPCA em inglês
    """
    r = _search(codigo, idioma)
    return _parse_metadata(r)[0]

import datetime
import math

from typing import Callable, Any

import finbr.dias_uteis as dus


DI_VALOR_NOMINAL = 100_000
_LETRA_CONTRATO_MES = {
    'F': 1,
    'G': 2,
    'H': 3,
    'J': 4,
    'K': 5,
    'M': 6,
    'N': 7,
    'Q': 8,
    'U': 9,
    'V': 10,
    'X': 11,
    'Z': 12,
}


def verifica_ticker(ticker: str):
    """Verifica se um ticker DI1 é válido.

    Parâmetros
    ----------
    ticker : str
        O ticker a ser verificado.

    Exemplos
    --------
    >>> verifica_ticker('DI1F24')  # Ticker válido
    >>> verifica_ticker('DI1X25')  # Ticker válido
    >>> verifica_ticker('DI1A24')  # Levanta ValueError (letra de contrato inválida)
    """
    if len(ticker) != 6:
        raise ValueError(f'ticker deve ter 6 caracteres, mas tem {len(ticker)}')

    if ticker[:3] != 'DI1':
        raise ValueError(f"ticker deve começar com 'DI1', mas começa com {ticker[:3]}")

    if ticker[3] not in _LETRA_CONTRATO_MES.keys():
        raise ValueError(f'letra de contrato inválida: {ticker[3]}')

    if not ticker[-2:].isdigit():
        raise ValueError(f'esperado 2 dígitos no final do ticker, mas tem {ticker[-2:]}')


def _verifica_ticker(func: Callable[..., Any]):
    def wrapper(ticker, *args, **kwargs):
        verifica_ticker(ticker)
        return func(ticker, *args, **kwargs)

    return wrapper


@_verifica_ticker
def vencimento(ticker: str) -> datetime.date:
    """Calcula a data de vencimento de um contrato DI1.

    Parâmetros
    ----------
    ticker : str
        O ticker DI1 para calcular a data de vencimento.

    Retorna
    -------
    datetime.date
        A data de vencimento do contrato, que é o primeiro dia útil
        do mês do contrato.

    Exemplos
    --------
    >>> vencimento('DI1F24')  # Retorna a data do primeiro dia útil de janeiro de 2024
    >>> vencimento('DI1X25')  # Retorna a data do primeiro dia útil de novembro de 2025
    """
    contrato = ticker[3]
    mes = _LETRA_CONTRATO_MES[contrato]
    ano = int('20' + ticker[-2:])

    data = datetime.date(ano, mes, 1)
    while True:
        if dus.dia_util(data):
            break
        data = data + datetime.timedelta(1)
    return data


@_verifica_ticker
def dias_vencimento(
    ticker: str,
    data: datetime.date | None = None,
    dias_uteis: bool = True,
) -> int:
    """Calcula o número de dias até o vencimento do contrato.

    Parâmetros
    ----------
    ticker : str
        O ticker DI1 para calcular os dias até o vencimento.
    data : datetime.date, opcional
        A data de referência para o cálculo. Se None, usa a data de hoje.
    dias_uteis : bool, padrão True
        Se True, retorna apenas dias úteis. Se False, retorna dias corridos.

    Retorna
    -------
    int
        Número de dias até o vencimento.

    Exemplos
    --------
    >>> dias_vencimento('DI1F24')  # Dias até o vencimento de janeiro de 2024
    >>> dias_vencimento('DI1X25', dias_uteis=False)  # Dias corridos até novembro de 2025
    """
    if not data:
        data = datetime.date.today()

    if dias_uteis:
        return dus.dif(data, vencimento(ticker))
    else:
        return (vencimento(ticker) - data).days


@_verifica_ticker
def preco_unitario(
    ticker: str,
    taxa: float,
    data: datetime.date | None = None,
) -> float:
    """Calcula o preço unitário (PU) de um contrato DI1.

    Parâmetros
    ----------
    ticker : str
        O ticker DI1 para calcular o preço.
    taxa : float
        A taxa de juros (em formato decimal, ex: 0.10 para 10%).
    data : datetime.date, opcional
        A data de referência para o cálculo. Se None, usa a data de hoje.

    Retorna
    -------
    float
        O preço unitário (PU) do contrato, arredondado para 2 casas decimais.

    Exemplos
    --------
    >>> preco_unitario('DI1F24', 0.10)  # Preço para o contrato de janeiro de 2024 a 10% a.a.
    >>> preco_unitario('DI1X25', 0.12, data=datetime.date(2023, 12, 1))  # Preço para data específica
    """
    if not data:
        data = datetime.date.today()

    dias = dias_vencimento(ticker=ticker, data=data)
    _pu = DI_VALOR_NOMINAL / ((1 + taxa) ** (dias / 252))
    return round(_pu, 2)


@_verifica_ticker
def taxa(
    ticker: str,
    preco_unitario: float,
    data: datetime.date | None = None,
) -> float:
    """Calcula a taxa de um contrato DI1 dado seu preço.

    Parâmetros
    ----------
    ticker : str
        O ticker DI1 para calcular a taxa.
    preco_unitario : float
        O preço unitário (PU) do contrato.
    data : datetime.date, opcional
        A data de referência para o cálculo. Se None, usa a data de hoje.

    Retorna
    -------
    float
        A taxa em formato decimal, arredondada para 5 casas decimais.

    Exemplos
    --------
    >>> taxa('DI1F24', 95000)  # Taxa para o contrato de janeiro de 2024 dado o preço
    >>> taxa('DI1X25', 90000, data=datetime.date(2023, 12, 1))  # Taxa para data específica
    """
    if not data:
        data = datetime.date.today()

    dias = dias_vencimento(ticker=ticker, data=data)
    taxa = math.exp((252 / dias) * math.log(DI_VALOR_NOMINAL / preco_unitario)) - 1
    return round(taxa, 5)


@_verifica_ticker
def dv01(
    ticker: str,
    taxa: float,
    data: datetime.date | None = None,
) -> float:
    """Calcula o DV01 (valor do contrato para variação de 1 basis point) de um DI1.

    Parâmetros
    ----------
    ticker : str
        O ticker DI1 para calcular o DV01.
    taxa : float
        A taxa de juros (em formato decimal, ex: 0.10 para 10%).
    data : datetime.date, opcional
        A data de referência para o cálculo. Se None, usa a data de hoje.

    Retorna
    -------
    float
        O DV01 do contrato, arredondado para 2 casas decimais.

    Exemplos
    --------
    >>> dv01('DI1F24', 0.10)  # DV01 para o contrato de janeiro de 2024 a 10% a.a.
    >>> dv01('DI1X25', 0.12, data=datetime.date(2023, 12, 1))  # DV01 para data específica
    """
    if not data:
        data = datetime.date.today()

    _preco = preco_unitario(ticker, taxa, data)
    _preco1 = preco_unitario(ticker, taxa + 0.0001, data)
    return round(_preco - _preco1, 2)

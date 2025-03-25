import datetime
import math

from typing import Callable, Any

import finbr.dias_uteis as dus


DI_FINAL_NOMINAL_VALUE = 100_000
_CONTRACT_LETTERS_MONTH = {
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


def verify_ticker(ticker: str):
    if len(ticker) != 6:
        raise ValueError(f'ticker length must be 6, got {len(ticker)}')

    if ticker[:3] != 'DI1':
        raise ValueError("ticker needs to start with 'DI1', got {ticker[:3]}")

    if ticker[3] not in _CONTRACT_LETTERS_MONTH.keys():
        raise ValueError(f'invalid ticker contract letter: {ticker[3]}')

    if not ticker[-2:].isdigit():
        raise ValueError(f'expected 2 digits at the end of ticker, got {ticker[-2:]}')


def _verify_ticker(func: Callable[..., Any]):
    def wrapper(ticker, *args, **kwargs):
        verify_ticker(ticker)
        return func(ticker, *args, **kwargs)

    return wrapper


@_verify_ticker
def vencimento(ticker: str) -> datetime.date:
    contract = ticker[3]
    month = _CONTRACT_LETTERS_MONTH[contract]
    year = int('20' + ticker[-2:])

    date = datetime.date(year, month, 1)
    while True:
        if dus.is_du(date):
            break
        date = date + datetime.timedelta(1)
    return date


@_verify_ticker
def dias_uteis_vencimento(
    ticker: str,
    date: datetime.date | None = None,
) -> int:
    if not date:
        date = datetime.date.today()

    return dus.diff(date, vencimento(ticker))


@_verify_ticker
def dias_corridos_vencimento(
    ticker: str,
    date: datetime.date | None = None,
) -> int:
    if not date:
        date = datetime.date.today()
    return (vencimento(ticker) - date).days


@_verify_ticker
def pu(
    ticker: str,
    taxa: float,
    date: datetime.date | None = None,
) -> float:
    if not date:
        date = datetime.date.today()

    days_to_maturity = dias_uteis_vencimento(ticker=ticker, date=date)
    _pu = DI_FINAL_NOMINAL_VALUE / ((1 + taxa) ** (days_to_maturity / 252))
    return round(_pu, 2)


@_verify_ticker
def taxa(
    ticker: str,
    pu: float,
    date: datetime.date | None = None,
) -> float:
    if not date:
        date = datetime.date.today()

    days_to_maturity = dias_uteis_vencimento(ticker=ticker, date=date)
    taxa = math.exp((252 / days_to_maturity) * math.log(DI_FINAL_NOMINAL_VALUE / pu)) - 1
    return round(taxa, 5)


@_verify_ticker
def dv01(
    ticker: str,
    taxa: float,
    date: datetime.date | None = None,
) -> float:
    if not date:
        date = datetime.date.today()

    _pu = pu(ticker, taxa, date)
    _pu1 = pu(ticker, taxa + 0.0001, date)
    return round(_pu - _pu1, 2)

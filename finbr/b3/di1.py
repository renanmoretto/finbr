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
    """Verify if a DI1 ticker is valid.

    Parameters
    ----------
    ticker : str
        The ticker to verify. Must be 6 characters long, starting with 'DI1',
        followed by a valid contract letter and 2 digits.

    Raises
    ------
    ValueError
        If the ticker length is not 6, doesn't start with 'DI1', has an invalid
        contract letter, or doesn't end with 2 digits.

    Examples
    --------
    >>> verify_ticker('DI1F24')  # Valid ticker
    >>> verify_ticker('DI1X25')  # Valid ticker
    >>> verify_ticker('DI1A24')  # Raises ValueError (invalid contract letter)
    """
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
def maturity_date(ticker: str) -> datetime.date:
    """Calculate the maturity date for a DI1 contract.

    Parameters
    ----------
    ticker : str
        The DI1 ticker to calculate maturity date for.

    Returns
    -------
    datetime.date
        The maturity date of the contract, which is the first business day
        of the contract month.

    Examples
    --------
    >>> maturity_date('DI1F24')  # Returns date for first business day of January 2024
    >>> maturity_date('DI1X25')  # Returns date for first business day of November 2025
    """
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
def days_to_maturity(
    ticker: str,
    date: datetime.date | None = None,
    business_days: bool = True,
) -> int:
    """Calculate the number of days until contract maturity.

    Parameters
    ----------
    ticker : str
        The DI1 ticker to calculate days to maturity for.
    date : datetime.date, optional
        The reference date to calculate days from. If None, uses today.
    business_days : bool, default True
        If True, returns only business days. If False, returns calendar days.

    Returns
    -------
    int
        Number of days until maturity.

    Examples
    --------
    >>> days_to_maturity('DI1F24')  # Days until January 2024 maturity
    >>> days_to_maturity('DI1X25', business_days=False)  # Calendar days until November 2025 maturity
    """
    if not date:
        date = datetime.date.today()

    if business_days:
        return dus.diff(date, maturity_date(ticker))
    else:
        return (maturity_date(ticker) - date).days


@_verify_ticker
def price(
    ticker: str,
    taxa: float,
    date: datetime.date | None = None,
) -> float:
    """Calculate the price (PU) of a DI1 contract.

    Parameters
    ----------
    ticker : str
        The DI1 ticker to calculate price for.
    taxa : float
        The interest rate (in decimal form, e.g., 0.10 for 10%).
    date : datetime.date, optional
        The reference date to calculate price for. If None, uses today.

    Returns
    -------
    float
        The price (PU) of the contract, rounded to 2 decimal places.

    Examples
    --------
    >>> price('DI1F24', 0.10)  # Price for January 2024 contract at 10% rate
    >>> price('DI1X25', 0.12, date=datetime.date(2023, 12, 1))  # Price for specific date
    """
    if not date:
        date = datetime.date.today()

    days = days_to_maturity(ticker=ticker, date=date)
    _pu = DI_FINAL_NOMINAL_VALUE / ((1 + taxa) ** (days / 252))
    return round(_pu, 2)


@_verify_ticker
def rate(
    ticker: str,
    pu: float,
    date: datetime.date | None = None,
) -> float:
    """Calculate the interest rate of a DI1 contract given its price.

    Parameters
    ----------
    ticker : str
        The DI1 ticker to calculate rate for.
    pu : float
        The price of the contract.
    date : datetime.date, optional
        The reference date to calculate rate for. If None, uses today.

    Returns
    -------
    float
        The interest rate in decimal form, rounded to 5 decimal places.

    Examples
    --------
    >>> rate('DI1F24', 95000)  # Rate for January 2024 contract at given price
    >>> rate('DI1X25', 90000, date=datetime.date(2023, 12, 1))  # Rate for specific date
    """
    if not date:
        date = datetime.date.today()

    days = days_to_maturity(ticker=ticker, date=date)
    taxa = math.exp((252 / days) * math.log(DI_FINAL_NOMINAL_VALUE / pu)) - 1
    return round(taxa, 5)


@_verify_ticker
def dv01(
    ticker: str,
    taxa: float,
    date: datetime.date | None = None,
) -> float:
    """Calculate the DV01 (dollar value of 1 basis point) of a DI1 contract.

    Parameters
    ----------
    ticker : str
        The DI1 ticker to calculate DV01 for.
    taxa : float
        The interest rate (in decimal form, e.g., 0.10 for 10%).
    date : datetime.date, optional
        The reference date to calculate DV01 for. If None, uses today.

    Returns
    -------
    float
        The DV01 of the contract, rounded to 2 decimal places.

    Examples
    --------
    >>> dv01('DI1F24', 0.10)  # DV01 for January 2024 contract at 10% rate
    >>> dv01('DI1X25', 0.12, date=datetime.date(2023, 12, 1))  # DV01 for specific date
    """
    if not date:
        date = datetime.date.today()

    _price = price(ticker, taxa, date)
    _price1 = price(ticker, taxa + 0.0001, date)
    return round(_price - _price1, 2)

import pandas as pd

from . import b3
from . import dias_uteis
from . import fundamentus
from . import sgs
from . import statusinvest
from ._yf import precos


def cdi(ao_ano: bool = True) -> float:
    """
    Get the CDI (Daily Interbank Deposit Rate) from the Brazilian Central Bank's SGS.

    Parameters
    ----------
    ao_ano : bool, default=True
        If True, return the ao_ano CDI. If False, return the latest daily CDI.

    Returns
    -------
    float
        The CDI rate.
    """
    cdi_data = sgs.get(12, data_inicio='2025-01-01')[12]
    if ao_ano:
        return round((1 + float(cdi_data.iloc[-1]) / 100) ** (252) - 1, 4)
    return float(cdi_data.iloc[-1]) / 100


def selic(ao_ano: bool = True) -> float:
    """
    Get the SELIC (Selic) rate from the Brazilian Central Bank's SGS.

    Parameters
    ----------
    ao_ano : bool, default=True
        If True, return the ao_ano SELIC. If False, return the latest daily SELIC.

    Returns
    -------
    float
        The SELIC rate.
    """
    selic_data = sgs.get(432, data_inicio='2025-01-01')[432]
    if ao_ano:
        return float(selic_data.iloc[-1]) / 100
    return round((1 + float(selic_data.iloc[-1]) / 100) ** (1 / 252) - 1, 4)


def ipca(start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """
    Get the monthly IPCA (Consumer Price Index) rate from the Brazilian Central Bank's SGS.

    Parameters
    ----------
    start : str, optional
        The start date of the period to get the IPCA.
    end : str, optional
        The end date of the period to get the IPCA.

    Returns
    -------
    pd.DataFrame
        The IPCA rate.
    """
    return sgs.get({433: 'ipca'}, start, end).div(100)

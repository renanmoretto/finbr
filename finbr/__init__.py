from . import sgs
from ._yf import prices

__all__ = [
    'sgs',
    'prices',
]


def cdi(annualized: bool = True) -> float:
    """
    Get the CDI (Daily Interbank Deposit Rate) from the Brazilian Central Bank's SGS.

    Parameters
    ----------
    annualized : bool, default=True
        If True, return the annualized CDI. If False, return the latest daily CDI.

    Returns
    -------
    float
        The CDI rate.
    """
    cdi_data = sgs.series(12, start='2025-01-01')
    if annualized:
        return round((1 + float(cdi_data.iloc[-1]) / 100) ** (252) - 1, 4)
    return float(cdi_data.iloc[-1]) / 100


def selic(annualized: bool = True) -> float:
    """
    Get the SELIC (Selic) rate from the Brazilian Central Bank's SGS.

    Parameters
    ----------
    annualized : bool, default=True
        If True, return the annualized SELIC. If False, return the latest daily SELIC.

    Returns
    -------
    float
        The SELIC rate.
    """
    selic_data = sgs.series(432, start='2025-01-01')
    if annualized:
        return float(selic_data.iloc[-1]) / 100
    return round((1 + float(selic_data.iloc[-1]) / 100) ** (1 / 252) - 1, 4)

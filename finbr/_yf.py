import datetime

import yfinance as yf
import pandas as pd


def prices(
    tickers: str | list[str],
    period: str = 'max',
    interval: str = '1d',
    start: str | datetime.date | None = None,
    end: str | datetime.date | None = None,
    adjusted: bool = True,
    sa: bool = True,
) -> pd.DataFrame:
    """
    Fetch historical price data for Brazilian stocks from Yahoo Finance.

    Parameters
    ----------
    tickers : str or list of str
        Ticker symbol(s) of the Brazilian stocks to fetch data for.
    period : str, default='max'
        Data period to download. Valid values: '1d', '5d', '1mo', '3mo', '6mo',
        '1y', '2y', '5y', '10y', 'ytd', 'max'.
    interval : str, default='1d'
        Data interval. Valid values: '1m', '2m', '5m', '15m', '30m', '60m', '90m',
        '1h', '1d', '5d', '1wk', '1mo', '3mo'.
    start : str or datetime.date, optional
        Start date for data retrieval. Format: 'YYYY-MM-DD'.
    end : str or datetime.date, optional
        End date for data retrieval. Format: 'YYYY-MM-DD'.
    adjusted : bool, default=True
        Whether to use adjusted close prices.
    sa : bool, default=True
        Whether to add the '.SA' suffix to the tickers.


    Returns
    -------
    pd.DataFrame
        DataFrame containing the historical price data.
    """
    tickers_list = tickers if isinstance(tickers, list) else [tickers]
    if sa:
        tickers_list_with_sa = [f'{ticker}.SA' for ticker in tickers_list]
    else:
        tickers_list_with_sa = tickers_list

    data_yf = yf.download(
        tickers_list_with_sa,
        period=period,
        interval=interval,
        start=start,
        end=end,
        auto_adjust=adjusted,
        progress=False,
    )
    if sa:
        data = data_yf.rename(columns=lambda x: x.replace('.SA', ''))
    else:
        data = data_yf
    return data

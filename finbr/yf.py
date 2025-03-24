import datetime

import yfinance as yf
import pandas as pd


def prices(
    tickers: str | list[str],
    period: str = 'max',
    interval: str = '1d',
    start_date: str | datetime.date | None = None,
    end_date: str | datetime.date | None = None,
    adjusted: bool = True,
) -> pd.DataFrame:
    tickers_list = tickers if isinstance(tickers, list) else [tickers]
    tickers_list_with_sa = [f'{ticker}.SA' for ticker in tickers_list]

    data_yf = yf.download(
        tickers_list_with_sa,
        period=period,
        interval=interval,
        start=start_date,
        end=end_date,
        auto_adjust=adjusted,
        progress=False,
    )
    data = data_yf.rename(columns=lambda x: x.replace('.SA', ''))
    return data

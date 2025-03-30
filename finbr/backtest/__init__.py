import datetime

import pandas as pd
import numpy as np

from dataclasses import dataclass


@dataclass
class BacktestResult:
    prices: pd.DataFrame
    values: pd.DataFrame
    exposure: pd.DataFrame
    result: pd.DataFrame
    all_dates: list
    rebal_dates: list


def _get_rebal_dates(all_dates: list[datetime.date], freq: str) -> list[datetime.date]:
    all_dates_dti = pd.DatetimeIndex(all_dates)
    dates = pd.DataFrame(index=all_dates_dti)
    dates['correct_date'] = dates.index
    dates = dates.resample(freq).last()
    _rebal_dates = all_dates_dti[all_dates_dti.isin(dates['correct_date'].values)].copy()
    return [d.date() for d in _rebal_dates]  # type: ignore


def _validate_weights(weights):
    if isinstance(weights, dict):
        if len(weights) == 0:
            raise ValueError('Dict for the weights has zero length.')

        if sum(weights.values()) > 1:
            raise ValueError('Dict for the weights has sum more than 1.')

        if sum(weights.values()) < 1:
            raise ValueError('Dict for the weights has sum less than 1.')

    if isinstance(weights, str) and weights not in ['ew']:
        raise ValueError(
            f"""Not a valid string value for weights parameter: {weights}.
                         If it isn't a dict, it has to be 'ew' (equal weight)"""
        )


def _simulate_without_rebalance(
    prices: pd.DataFrame, starting_weights: dict | str = 'ew'
) -> BacktestResult:
    _validate_weights(starting_weights)

    if starting_weights == 'ew':
        values = prices.pct_change().fillna(0).add(1).cumprod()
        sim_result = values.sum(axis=1).pct_change().fillna(0).add(1).cumprod()

    if isinstance(starting_weights, dict):
        tickers = prices.columns.to_list()

        normalized_prices = prices.pct_change().fillna(0).add(1).cumprod()

        weighted_values = pd.DataFrame()
        for ticker in tickers:
            weighted_values[ticker] = normalized_prices[ticker].mul(starting_weights[ticker])
        values = weighted_values.sum(axis=1)
        sim_result = values.pct_change().fillna(0).add(1).cumprod()

    sim_result.index.name = 'date'
    sim_result.columns = ['sim']

    total_value = values.sum(axis=1)
    exposure = values.apply(lambda row: row / total_value.loc[row.name], axis=1)

    return BacktestResult(
        prices=prices,
        values=values,
        exposure=exposure,
        result=sim_result,
        all_dates=sim_result.index.to_list(),
        rebal_dates=[],
    )


def _simulate_with_rebalance(
    prices: pd.DataFrame,
    rebal_weights: dict | str = 'ew',
    rebal_freq: str = '1M',
) -> BacktestResult:
    _validate_weights(rebal_weights)

    tickers = prices.columns.to_list()
    n_tickers = len(prices.columns)

    if rebal_weights == 'ew':
        weights = pd.Series(index=tickers, dtype=np.float64).fillna(1 / n_tickers).to_dict()
    if isinstance(rebal_weights, dict):
        weights = rebal_weights.copy()

    returns_array = prices.pct_change().fillna(0).values

    all_dates_array = prices.index.values

    rebal_dates = _get_rebal_dates(prices, rebal_freq)
    rebal_dates_array = np.insert(rebal_dates.values, 0, all_dates_array[0])  # first day

    values = np.zeros((len(all_dates_array), len(tickers)))
    total_value = []
    for i, date in enumerate(all_dates_array):
        for j, ticker in enumerate(tickers):
            if i == 0:
                values[i, j] = 1 * weights.get(ticker)
            else:
                if all_dates_array[i - 1] in rebal_dates_array:
                    values[i, j] = (total_value[i - 1] * weights.get(ticker)) * (
                        1 + returns_array[i, j]
                    )
                else:
                    values[i, j] = values[i - 1, j] * (1 + returns_array[i, j])
        total_value.append(values[i, :].sum())

    exposure = values / np.array(total_value)[:, np.newaxis]

    values = pd.DataFrame(values, index=all_dates_array, columns=tickers)
    exposure = pd.DataFrame(exposure, index=all_dates_array, columns=tickers)
    sim_result = pd.DataFrame(total_value, index=all_dates_array, columns=['sim'])

    return BacktestResult(
        prices=prices,
        values=values,
        exposure=exposure,
        result=sim_result,
        all_dates=prices.index,
        rebal_dates=rebal_dates,
    )


def backtest(
    prices,
    weights: str | dict = 'ew',
    rebal_freq: str | None = None,
) -> BacktestResult:
    """
    Run the backtest simulation.

    Parameters
    ----------
    prices : pd.DataFrame
        DataFrame containing price data for the assets.
    weights : str | dict, default='ew' (equal weight)
        If dict, weights for each asset (numbers between 0 and 1).
        The sum must equal 1.
        Example:
            asset_weights = {
                'asset1': 0.3,
                'asset2': 0.2,
                'asset3': 0.5,
            }
        If 'ew', runs the simulation using equal weight for all assets (1 / number of assets).
    rebal_freq : str | None, default=None
        Rebalance frequency. Has the same valid inputs as pandas.DataFrame.resample() function.

    Returns
    -------
    BacktestResult
        Object containing the backtest results including prices, values, exposure, and dates.
    """
    import warnings

    warnings.warn(
        'The backtest function is in development. Results may be inaccurate.',
        UserWarning,
    )

    if rebal_freq:
        return _simulate_with_rebalance(prices=prices, rebal_weights=weights, rebal_freq=rebal_freq)
    else:
        return _simulate_without_rebalance(prices=prices, starting_weights=weights)

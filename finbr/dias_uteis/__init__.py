import datetime

from .base import Holiday
from .holidays import NATIONAL_HOLIDAYS


def _get_year_holidays(year: int, holidays: list[Holiday]) -> list[datetime.date]:
    holidays_dates = []
    for holiday in holidays:
        holiday_date = holiday.calc_for_year(year)
        if holiday_date is not None:
            holidays_dates.append(holiday_date)
    return holidays_dates


def _get_year_dus(year: int, holidays: list[Holiday] | None = None) -> list[datetime.date]:
    if holidays:
        year_holidays = _get_year_holidays(year, holidays)
    else:
        year_holidays = []
    date = datetime.date(year, 1, 1)
    last_date_of_year = datetime.date(year, 12, 31)
    dates = []
    while date <= last_date_of_year:
        if date.weekday() < 5 and date not in year_holidays:
            dates.append(date)
        date += datetime.timedelta(days=1)
    return dates


def _get_years_between_two_dates(start_date: datetime.date, end_date: datetime.date) -> list[int]:
    if end_date > start_date:
        years = [year for year in range(start_date.year, end_date.year + 1)]
    else:
        years = [year for year in range(start_date.year, end_date.year - 1, -1)]
    return sorted(years)


def _get_all_dus_for_years(years: list[int]) -> list[datetime.date]:
    all_dus = []
    for year in years:
        all_dus += _get_year_dus(year, NATIONAL_HOLIDAYS)
    return all_dus


def _find_du(start_date: datetime.date, direction: int) -> datetime.date:
    date = start_date
    while not is_du(date):
        date += datetime.timedelta(days=direction)
    return date


def is_du(date: datetime.date) -> bool:
    """
    Checks if a given date is a business day.

    Parameters
    ----------
    date : datetime.date
        The date to be checked.

    Returns
    -------
    bool
        Returns True if the date is a business day, False otherwise.
    """
    if isinstance(date, datetime.datetime):
        date = date.date()
    year_dus = _get_year_dus(date.year, NATIONAL_HOLIDAYS)
    if date in year_dus:
        return True
    return False


def is_holiday(date: datetime.date) -> bool:
    """
    Checks if a given date is a holiday.

    Parameters
    ----------
    date : datetime.date
        The date to be checked.

    Returns
    -------
    bool
        Returns True if the date is a holiday, False otherwise.
    """
    holidays = _get_year_holidays(date.year, NATIONAL_HOLIDAYS)
    if date in holidays:
        return True
    return False


def delta_du(from_date: datetime.date, days_delta: int) -> datetime.date:
    """
    Calculates the date a certain number of business days from a specified date.

    Parameters
    ----------
    from_date : datetime.date
        The starting date.
    days_delta : int
        The number of business days to be added to from_date.

    Returns
    -------
    datetime.date
        The calculated business day date.
    """
    if not is_du(from_date):
        raise ValueError("'date' is not a business day")

    # days_delta*2 so the bday of the end year is always inside the list all_dus
    start_calendar_date = from_date + datetime.timedelta(days=-days_delta * 4)
    end_calendar_date = from_date + datetime.timedelta(days=days_delta * 4)
    years = _get_years_between_two_dates(start_calendar_date, end_calendar_date)
    all_dus = _get_all_dus_for_years(years)

    date_position = all_dus.index(from_date)
    return all_dus[date_position + days_delta]


def last_du(date: datetime.date | None = None) -> datetime.date:
    """
    Finds the last business day relative to today.

    Returns
    -------
    datetime.date
        The date of the last business day.
    """
    if not date:
        date = datetime.date.today()

    if not is_du(date):
        date = _find_du(date, 1)  # find next du

    return delta_du(date, -1)


def next_du(date: datetime.date | None = None) -> datetime.date:
    """
    Finds the next business day relative to today.

    Returns
    -------
    datetime.date
        The date of the next business day.
    """
    if not date:
        date = datetime.date.today()

    if not is_du(date):
        date = _find_du(date, -1)  # find last du

    return delta_du(date, 1)


def range_du(
    start: datetime.date,
    end: datetime.date,
    include_end: bool = False,
) -> list[datetime.date]:
    """
    Returns a list of business days within a specified range.

    Parameters
    ----------
    start : datetime.date
        The start date of the range.
    end : datetime.date
        The end date of the range.
    include_end : bool, optional
        If True, includes the end date in the range interval, default False.
        By default, Python's range() is closed on the start and open on the
        end of the interval, like [i,f[.

    Returns
    -------
    list[datetime.date]
        A list of business days within the specified range.
    """
    years = _get_years_between_two_dates(start, end)
    all_dus = _get_all_dus_for_years(years)
    if include_end:
        return [du for du in all_dus if du >= start and du <= end]
    else:
        return [du for du in all_dus if du >= start and du < end]


def year_dus(year: int) -> list[datetime.date]:
    """
    Returns a list of all business days for a given year.

    Parameters
    ----------
    year : int
        The year for which to calculate the business days.

    Returns
    -------
    list[datetime.date]
        A list containing all business days in the specified year.
    """
    return range_du(datetime.date(year, 1, 1), datetime.date(year, 12, 31), True)


def year_holidays(year: int) -> list[datetime.date]:
    """
    Returns a list of all holidays for a given year.

    If holidays are defined in the object, this method returns a list of those holidays
    for the specified year. If no holidays are defined, returns an empty list.

    Parameters
    ----------
    year : int
        The year for which to retrieve the holidays.

    Returns
    -------
    list[datetime.date]
        A list containing all holidays for the specified year, or an empty list if
        no holidays are defined.
    """
    return _get_year_holidays(year, NATIONAL_HOLIDAYS)


def diff(a: datetime.date, b: datetime.date) -> int:
    """
    Calculates the number of business days between two dates (b-a).

    Parameters
    ----------
    a : datetime.date
    b : datetime.date

    Returns
    -------
    int
        Number of business days between dates 'a' and 'b'.
    """
    _years = {a.year, b.year}
    years = list(range(min(_years), max(_years) + 1))
    all_dus = _get_all_dus_for_years(years)
    _min_date, _max_date = sorted((a, b))
    dus = [_date for _date in all_dus if _min_date <= _date <= _max_date]
    return (len(dus) - 1) * (1 if b > a else -1)

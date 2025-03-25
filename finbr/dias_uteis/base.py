import datetime
from typing import Callable


class Holiday:
    """
    A class representing a holiday.

    Parameters
    ----------
    month : int, optional
        The month when the holiday occurs if it's a fixed date, default None.
    day : int, optional
        The day of the month when the holiday occurs if it's a fixed date, default None.
    func : Callable[[int], datetime.date], optional
        A function that takes a year as an argument and returns the date of the holiday for
        that year if it's a dynamic date, default None.
    start_year : int, optional
        The year when the holiday starts to occur, default None. This is not used for dynamic holidays.
    end_year : int, optional
        The year when the holiday stops to occur, default None. This is not used for dynamic holidays.
        Note: This year will be considered as the last year the holiday will occur.

    Methods
    -------
    calc_for_year(year: int) -> datetime.date
        Calculate the date of the holiday for the given year.

    Notes
    -----
        'func' will be ignored if 'day' and 'month' are provided. The holiday's
        type in this case will be 'fixed'.

        If 'func' is provided and 'day' or 'month' is None, the holiday's type
        will be 'dynamic'.
    """

    def __init__(
        self,
        month: int | None = None,
        day: int | None = None,
        func: Callable[[int], datetime.date] | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
    ):
        _month_day_passed = month is not None and day is not None
        if _month_day_passed:
            if not isinstance(month, int) or not isinstance(day, int):
                raise TypeError("'month' and 'day' types must be int")

            # Validating month/day values
            _year_for_validation = datetime.date.today().year
            datetime.date(_year_for_validation, month, day)

            _type = 'fixed'
        else:
            if func is None:
                raise ValueError("'func' is required if 'month' and 'day' are both None")
            if not callable(func):
                raise TypeError("'func' must be a callable")
            _type = 'dynamic'

        self.month = month
        self.day = day
        self.func = func
        self.start_year = start_year
        self.end_year = end_year
        self._type = _type

    def calc_for_year(self, year: int) -> datetime.date | None:
        """
        Calculate the exact date of the holiday for the specified year.

        Parameters
        ----------
        year : int
            The year to calculate the holiday's date.

        Returns
        -------
        datetime.date
            The date of the holiday for the specified year.
        """
        # Just to validate the year value.
        # Values like -5 or 60000 are invalid.
        datetime.date(year, 1, 1)

        if self._type == 'fixed':
            if self.start_year is not None and year < self.start_year:
                return None
            if self.end_year is not None and year > self.end_year:
                return None
            return datetime.date(year, self.month, self.day)  # type: ignore
        else:
            func_response = self.func(year)  # type: ignore
            if not isinstance(func_response, datetime.date):
                raise TypeError("'func' must return a datetime.date")
            return func_response

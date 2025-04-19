import random
import datetime
import unittest

import finbr.dias_uteis as dus


class TestDiasUteis(unittest.TestCase):
    def test_is_du(self):
        du = datetime.date(2023, 11, 3)
        assert dus.dia_util(du)

    def test_is_not_du(self):
        du = datetime.date(2023, 11, 2)  # Feriado 2/11
        du1 = datetime.date(2020, 2, 22)  # Terça de carnaval 2020
        assert not dus.dia_util(du)
        assert not dus.dia_util(du1)

    def test_is_holiday(self):
        assert dus.feriado(datetime.date(2020, 6, 11))  # Corpus Christi 2020

    def test_delta_du(self):
        date = datetime.date(2023, 12, 15)
        assert dus.delta(date, 5) == datetime.date(2023, 12, 22)
        assert dus.delta(date, -10) == datetime.date(2023, 12, 1)

    def test_next_du(self):
        today = datetime.date.today()
        next_du = dus.proximo()
        assert isinstance(next_du, datetime.date)
        assert next_du > today

        if dus.dia_util(today):
            assert dus.dif(today, next_du) == 1

        assert dus.dia_util(next_du)

    def test_next_du_with_date(self):
        date = datetime.date(2024, 1, 17)
        next_du = dus.proximo(date)
        assert isinstance(next_du, datetime.date)
        assert next_du > date
        assert dus.dif(date, next_du) == 1
        assert dus.dia_util(next_du)

        date = datetime.date(2024, 1, 1)
        next_du = dus.proximo(date)
        assert isinstance(next_du, datetime.date)
        assert next_du > date
        assert dus.dif(date, next_du) == 0
        assert dus.dia_util(next_du)

    def test_next_du_both(self):
        today = datetime.date.today()
        next_du1 = dus.proximo()
        next_du2 = dus.proximo(today)
        assert next_du1 == next_du2

    def test_last_du(self):
        today = datetime.date.today()
        last_du = dus.ultimo()
        assert isinstance(last_du, datetime.date)
        assert last_du < today

        if dus.dia_util(today):
            assert dus.dif(today, last_du) == -1

        assert dus.dia_util(last_du)

    def test_last_du_with_date(self):
        date = datetime.date(2024, 1, 17)
        last_du = dus.ultimo(date)
        assert isinstance(last_du, datetime.date)
        assert last_du < date
        assert dus.dif(date, last_du) == -1
        assert dus.dia_util(last_du)

        date = datetime.date(2024, 1, 1)
        last_du = dus.ultimo(date)
        assert isinstance(last_du, datetime.date)
        assert last_du < date
        assert dus.dif(date, last_du) == 0
        assert dus.dia_util(last_du)

    def test_last_du_both(self):
        today = datetime.date.today()
        last_du1 = dus.ultimo()
        last_du2 = dus.ultimo(today)
        assert last_du1 == last_du2

    def test_range_du(self):
        range_dus = dus.intervalo(datetime.date(2023, 11, 1), datetime.date(2023, 11, 30))

        nov2023_dus_sample = [
            datetime.date(2023, 11, 1),
            datetime.date(2023, 11, 3),
            datetime.date(2023, 11, 6),
            datetime.date(2023, 11, 7),
            datetime.date(2023, 11, 8),
            datetime.date(2023, 11, 9),
            datetime.date(2023, 11, 10),
            datetime.date(2023, 11, 13),
            datetime.date(2023, 11, 14),
            datetime.date(2023, 11, 16),
            datetime.date(2023, 11, 17),
            datetime.date(2023, 11, 20),
            datetime.date(2023, 11, 21),
            datetime.date(2023, 11, 22),
            datetime.date(2023, 11, 23),
            datetime.date(2023, 11, 24),
            datetime.date(2023, 11, 27),
            datetime.date(2023, 11, 28),
            datetime.date(2023, 11, 29),
        ]

        assert len(range_dus) == 19
        assert len(range_dus) == len(nov2023_dus_sample)

        for du, du_sample in zip(range_dus, nov2023_dus_sample):
            assert du == du_sample
            assert dus.dia_util(du)

    def test_year_dus(self):
        year_dus = dus.dias_uteis_ano(2023)
        for du in year_dus:
            assert dus.dia_util(du)
        assert len(year_dus) == 249

    def test_year_holidays(self):
        year_holidays = dus.feriados_ano(2023)
        holidays_2023_sample = [
            datetime.date(2023, 1, 1),
            datetime.date(2023, 2, 20),
            datetime.date(2023, 2, 21),
            datetime.date(2023, 4, 7),
            datetime.date(2023, 4, 21),
            datetime.date(2023, 5, 1),
            datetime.date(2023, 6, 8),
            datetime.date(2023, 9, 7),
            datetime.date(2023, 10, 12),
            datetime.date(2023, 11, 2),
            datetime.date(2023, 11, 15),
            datetime.date(2023, 12, 25),
        ]

        assert len(year_holidays) == len(holidays_2023_sample)
        assert len(year_holidays) == 12
        for holiday, holiday_sample in zip(year_holidays, holidays_2023_sample):
            assert holiday == holiday_sample
            assert not dus.dia_util(holiday)

    def test_diff(self):
        assert dus.dif(datetime.date(2024, 11, 4), datetime.date(2024, 11, 11)) == 5
        assert dus.dif(datetime.date(2024, 11, 4), datetime.date(2024, 11, 18)) == 9
        assert dus.dif(datetime.date(2024, 11, 11), datetime.date(2024, 11, 4)) == -5
        assert dus.dif(datetime.date(2024, 11, 18), datetime.date(2024, 11, 4)) == -9
        assert dus.dif(datetime.date(2024, 11, 11), datetime.date(2034, 1, 2)) == 2290
        assert dus.dif(datetime.date(2034, 1, 2), datetime.date(2024, 11, 11)) == -2290

    def test_consciencia_negra(self):
        # started in 2024
        assert dus.dia_util(datetime.date(2014, 11, 20))
        assert dus.dia_util(datetime.date(2023, 11, 20))
        assert not dus.dia_util(datetime.date(2024, 11, 20))
        assert not dus.dia_util(datetime.date(2025, 11, 20))
        assert not dus.dia_util(datetime.date(2026, 11, 20))

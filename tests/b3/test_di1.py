import datetime
import random
from unittest import TestCase

from finbr.b3 import di1


class TestTickerVerifier(TestCase):
    def test_random_tickers(self):
        letters = list(di1._CONTRACT_LETTERS_MONTH.keys())
        tickers = [f'DI1{letter}{random.randint(10, 99)}' for letter in letters]
        for ticker in tickers:
            di1.verify_ticker(ticker)

    def test_wrong_contract_letter(self):
        with self.assertRaises(ValueError) as _:
            di1.verify_ticker('DI1B30')

    def test_ticker_wrong_start(self):
        with self.assertRaises(ValueError) as _:
            di1.verify_ticker('ABGF3B')

    def test_wrong_end(self):
        with self.assertRaises(ValueError) as _:
            di1.verify_ticker('DI1F3A')


class TestDIUtils(TestCase):
    def test_maturity_date(self):
        assert di1.maturity_date('DI1F30') == datetime.date(2030, 1, 2)
        assert di1.maturity_date('DI1N25') == datetime.date(2025, 7, 1)
        assert di1.maturity_date('DI1F18') == datetime.date(2018, 1, 2)
        assert di1.maturity_date('DI1N27') == datetime.date(2027, 7, 1)
        assert di1.maturity_date('DI1J26') == datetime.date(2026, 4, 1)
        assert di1.maturity_date('DI1H24') == datetime.date(2024, 3, 1)

    def test_price_date_none(self):
        pu = di1.price('DI1F30', 0.1140)
        assert isinstance(pu, float)
        assert pu > 0
        assert pu <= di1.DI_FINAL_NOMINAL_VALUE

    def test_price_with_date(self):
        pu = di1.price('DI1F30', 0.1140, datetime.date(2024, 4, 24))
        assert isinstance(pu, float)
        assert pu > 0
        assert pu <= di1.DI_FINAL_NOMINAL_VALUE
        assert pu == 54332.72

    def test_rate_without_date(self):
        taxa = di1.rate('DI1F30', 54332.72)
        assert taxa > 0

    def test_rate_with_date(self):
        taxa = di1.rate('DI1F30', 54332.72, datetime.date(2024, 4, 24))
        assert taxa > 0
        assert taxa == 0.114

    def test_dv01_without_date(self):
        dv01 = di1.dv01('DI1F30', 0.1156)
        assert dv01 > 0

    def test_dv01_with_date(self):
        dv01 = di1.dv01('DI1F30', 0.1156, datetime.date(2024, 4, 24))
        assert dv01 > 0
        assert dv01 == 27.29

    def test_days_to_maturity_with_business_days(self):
        days = di1.days_to_maturity('DI1F30', datetime.date(2024, 4, 24))
        assert days == 1424

    def test_days_to_maturity_without_business_days(self):
        days = di1.days_to_maturity('DI1F30', datetime.date(2024, 4, 24), business_days=False)
        assert days == 2079

    def test_days_to_maturity_different_contracts(self):
        date = datetime.date(2024, 4, 24)
        days_f30 = di1.days_to_maturity('DI1F30', date)
        days_n25 = di1.days_to_maturity('DI1N25', date)
        days_j26 = di1.days_to_maturity('DI1J26', date)
        assert days_f30 > days_n25
        assert days_n25 < days_j26

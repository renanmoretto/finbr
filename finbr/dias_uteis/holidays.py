import datetime
from functools import partial

from .base import Holiday


def _calc_pascoa(year: int) -> datetime.date:
    """
    Calculates Easter date using the Meeus/Jones/Butcher algorithm.
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(year, month, day)


def _delta_pascoa(year: int, delta: int) -> datetime.date:
    """
    Calculates the date relative to Easter in the given year.

    Dates:
    Carnival:
        Carnival Tuesday: 47 days before Easter.
        Carnival Monday: 48 days before Easter.
    Good Friday: 2 days before Easter.
    Corpus Christi: 60 days after Easter.
    """
    pascoa = _calc_pascoa(year)
    return pascoa + datetime.timedelta(days=delta)


_calc_segunda_feira_carnaval = partial(_delta_pascoa, delta=-48)
_calc_terca_feira_carnaval = partial(_delta_pascoa, delta=-47)
_calc_sexta_feira_santa = partial(_delta_pascoa, delta=-2)
_calc_corpus_christi = partial(_delta_pascoa, delta=60)


NATIONAL_HOLIDAYS = [
    Holiday(month=1, day=1),  # Ano novo
    Holiday(func=_calc_segunda_feira_carnaval),  # Segunda-feira de carnaval
    Holiday(func=_calc_terca_feira_carnaval),  # Terça-feira de carnaval
    Holiday(func=_calc_sexta_feira_santa),  # Sexta-feira Santa
    Holiday(month=4, day=21),  # Tiradentes
    Holiday(month=5, day=1),  # Dia do Trabalho
    Holiday(func=_calc_corpus_christi),  # Corpus Christi
    Holiday(month=9, day=7),  # Independência
    Holiday(month=10, day=12),  # Nossa Senhora Aparecida
    Holiday(month=11, day=2),  # Finados
    Holiday(month=11, day=15),  # Proclamação da República
    Holiday(month=11, day=20, start_year=2024),  # Consciência Negra
    Holiday(month=12, day=25),  # Natal
]

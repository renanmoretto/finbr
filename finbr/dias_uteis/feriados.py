import datetime
from functools import partial

from .base import Feriado


def _calc_pascoa(ano: int) -> datetime.date:
    """
    Datas da páscoa usando o algoritmo de Meeus/Jones/Butcher.
    """
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(ano, mes, dia)


def _delta_pascoa(ano: int, delta: int) -> datetime.date:
    """
    Calcula a data relativa à páscoa no ano fornecido.

    Datas:
    Carnaval:
        Segunda-feira de carnaval: 47 dias antes da páscoa.
        Terça-feira de carnaval: 48 dias antes da páscoa.
    Sexta-feira Santa: 2 dias antes da páscoa.
    Corpus Christi: 60 dias após a páscoa.
    """
    pascoa = _calc_pascoa(ano)
    return pascoa + datetime.timedelta(days=delta)


_calc_segunda_feira_carnaval = partial(_delta_pascoa, delta=-48)
_calc_terca_feira_carnaval = partial(_delta_pascoa, delta=-47)
_calc_sexta_feira_santa = partial(_delta_pascoa, delta=-2)
_calc_corpus_christi = partial(_delta_pascoa, delta=60)


FERIADOS_NACIONAIS = [
    Feriado(mes=1, dia=1),  # Ano novo
    Feriado(func=_calc_segunda_feira_carnaval),  # Segunda-feira de carnaval
    Feriado(func=_calc_terca_feira_carnaval),  # Terça-feira de carnaval
    Feriado(func=_calc_sexta_feira_santa),  # Sexta-feira Santa
    Feriado(mes=4, dia=21),  # Tiradentes
    Feriado(mes=5, dia=1),  # Dia do Trabalho
    Feriado(func=_calc_corpus_christi),  # Corpus Christi
    Feriado(mes=9, dia=7),  # Independência
    Feriado(mes=10, dia=12),  # Nossa Senhora Aparecida
    Feriado(mes=11, dia=2),  # Finados
    Feriado(mes=11, dia=15),  # Proclamação da República
    Feriado(mes=11, dia=20, ano_inicio=2024),  # Consciência Negra
    Feriado(mes=12, dia=25),  # Natal
]

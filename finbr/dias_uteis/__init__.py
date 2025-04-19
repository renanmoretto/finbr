import datetime

from .base import Feriado
from .feriados import FERIADOS_NACIONAIS


def _feriados_ano(year: int, holidays: list[Feriado]) -> list[datetime.date]:
    holidays_dates = []
    for holiday in holidays:
        holiday_date = holiday.calc_para_ano(year)
        if holiday_date is not None:
            holidays_dates.append(holiday_date)
    return holidays_dates


def _dus_ano(year: int, holidays: list[Feriado] | None = None) -> list[datetime.date]:
    if holidays:
        year_holidays = _feriados_ano(year, holidays)
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


def _anos_entre_duas_datas(start_date: datetime.date, end_date: datetime.date) -> list[int]:
    if end_date > start_date:
        years = [year for year in range(start_date.year, end_date.year + 1)]
    else:
        years = [year for year in range(start_date.year, end_date.year - 1, -1)]
    return sorted(years)


def _get_all_dus_for_years(years: list[int]) -> list[datetime.date]:
    all_dus = []
    for year in years:
        all_dus += _dus_ano(year, FERIADOS_NACIONAIS)
    return all_dus


def _find_du(start_date: datetime.date, direction: int) -> datetime.date:
    date = start_date
    while not dia_util(date):
        date += datetime.timedelta(days=direction)
    return date


def dia_util(data: datetime.date) -> bool:
    """
    Verifica se uma data é um dia útil.

    Parâmetros
    ----------
    date : datetime.date
        A data a ser verificada.

    Retorna
    -------
    bool
        Retorna True se a data for um dia útil, False caso contrário.
    """
    if isinstance(data, datetime.datetime):
        data = data.date()
    year_dus = _dus_ano(data.year, FERIADOS_NACIONAIS)
    if data in year_dus:
        return True
    return False


def feriado(data: datetime.date) -> bool:
    """
    Verifica se uma data é um feriado.

    Parâmetros
    ----------
    date : datetime.date
        A data a ser verificada.

    Retorna
    -------
    bool
        Retorna True se a data for um feriado, False caso contrário.
    """
    feriados = _feriados_ano(data.year, FERIADOS_NACIONAIS)
    if data in feriados:
        return True
    return False


def delta(data: datetime.date, dias: int) -> datetime.date:
    """
    Calcula a data a um certo número de dias úteis a partir de uma data especificada.

    Parâmetros
    ----------
    from_date : datetime.date
        A data inicial.
    days_delta : int
        O número de dias úteis a serem somados à data inicial.

    Retorna
    -------
    datetime.date
        A data útil calculada.
    """
    if not dia_util(data):
        raise ValueError("'data' não é um dia útil")

    # days_delta*2 so the bday of the end year is always inside the list all_dus
    start_calendar_date = data + datetime.timedelta(days=-dias * 4)
    end_calendar_date = data + datetime.timedelta(days=dias * 4)
    anos = _anos_entre_duas_datas(start_calendar_date, end_calendar_date)
    dus = _get_all_dus_for_years(anos)

    posicao_data = dus.index(data)
    return dus[posicao_data + dias]


def ultimo(data: datetime.date | None = None) -> datetime.date:
    """
    Encontra o último dia útil relativo a hoje.

    Retorna
    -------
    datetime.date
        A data do último dia útil.
    """
    if not data:
        data = datetime.date.today()

    if not dia_util(data):
        data = _find_du(data, 1)  # find next du

    return delta(data, -1)


def proximo(data: datetime.date | None = None) -> datetime.date:
    """
    Encontra o próximo dia útil relativo a hoje.

    Retorna
    -------
    datetime.date
        A data do próximo dia útil.
    """
    if not data:
        data = datetime.date.today()

    if not dia_util(data):
        data = _find_du(data, -1)  # find last du

    return delta(data, 1)


def intervalo(
    inicio: datetime.date,
    fim: datetime.date,
    incluir_fim: bool = False,
) -> list[datetime.date]:
    """
    Retorna uma lista de dias úteis dentro de um intervalo especificado.

    Parâmetros
    ----------
    start : datetime.date
        Data inicial do intervalo.
    end : datetime.date
        Data final do intervalo.
    include_end : bool, opcional
        Se True, inclui a data final no intervalo, padrão False.
        Por padrão, o range() do Python é fechado no início e aberto no fim do intervalo, como [i,f[.

    Retorna
    -------
    list[datetime.date]
        Uma lista de dias úteis dentro do intervalo especificado.
    """
    anos = _anos_entre_duas_datas(inicio, fim)
    dus = _get_all_dus_for_years(anos)
    if incluir_fim:
        return [du for du in dus if du >= inicio and du <= fim]
    else:
        return [du for du in dus if du >= inicio and du < fim]


def dias_uteis_ano(ano: int) -> list[datetime.date]:
    """
    Retorna uma lista de todos os dias úteis de um determinado ano.

    Parâmetros
    ----------
    year : int
        O ano para o qual calcular os dias úteis.

    Retorna
    -------
    list[datetime.date]
        Uma lista contendo todos os dias úteis do ano especificado.
    """
    return intervalo(datetime.date(ano, 1, 1), datetime.date(ano, 12, 31), True)


def feriados_ano(ano: int) -> list[datetime.date]:
    """
    Retorna uma lista de todos os feriados de um determinado ano.

    Se houver feriados definidos no objeto, este método retorna uma lista desses feriados
    para o ano especificado. Se não houver feriados definidos, retorna uma lista vazia.

    Parâmetros
    ----------
    year : int
        O ano para o qual recuperar os feriados.

    Retorna
    -------
    list[datetime.date]
        Uma lista contendo todos os feriados do ano especificado, ou uma lista vazia se
        não houver feriados definidos.
    """
    return _feriados_ano(ano, FERIADOS_NACIONAIS)


def dif(a: datetime.date, b: datetime.date) -> int:
    """
    Calcula o número de dias úteis entre duas datas (b-a).

    Parâmetros
    ----------
    a : datetime.date
    b : datetime.date

    Retorna
    -------
    int
        Número de dias úteis entre as datas 'a' e 'b'.
    """
    _years = {a.year, b.year}
    years = list(range(min(_years), max(_years) + 1))
    all_dus = _get_all_dus_for_years(years)
    _min_date, _max_date = sorted((a, b))
    dus = [_date for _date in all_dus if _min_date <= _date <= _max_date]
    return (len(dus) - 1) * (1 if b > a else -1)

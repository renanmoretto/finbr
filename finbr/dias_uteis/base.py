import datetime
from typing import Callable


class Feriado:
    """
    Uma classe que representa um feriado.

    Parâmetros
    ----------
    mes : int, opcional
        O mês em que o feriado ocorre se for uma data fixa, padrão None.
    dia : int, opcional
        O dia do mês em que o feriado ocorre se for uma data fixa, padrão None.
    func : Callable[[int], datetime.date], opcional
        Uma função que recebe um ano como argumento e retorna a data do feriado para
        aquele ano se for uma data dinâmica, padrão None.
    ano_inicio : int, opcional
        O ano em que o feriado começa a ocorrer, padrão None. Não é usado para feriados dinâmicos.
    ano_fim : int, opcional
        O ano em que o feriado deixa de ocorrer, padrão None. Não é usado para feriados dinâmicos.
        Nota: Este ano será considerado como o último ano em que o feriado ocorrerá.

    Métodos
    -------
    calc_para_ano(ano: int) -> datetime.date
        Calcula a data do feriado para o ano fornecido.

    Notas
    -----
        'func' será ignorado se 'dia' e 'mes' forem fornecidos. O tipo do feriado
        neste caso será 'fixo'.

        Se 'func' for fornecida e 'dia' ou 'mes' for None, o tipo do feriado
        será 'dinâmico'.
    """

    def __init__(
        self,
        mes: int | None = None,
        dia: int | None = None,
        func: Callable[[int], datetime.date] | None = None,
        ano_inicio: int | None = None,
        ano_fim: int | None = None,
    ):
        _mes_dia_passado = mes is not None and dia is not None
        if _mes_dia_passado:
            if not isinstance(mes, int) or not isinstance(dia, int):
                raise TypeError("'mes' e 'dia' devem ser do tipo int")

            # Validação dos valores de mês/dia
            _ano_para_validacao = datetime.date.today().year
            datetime.date(_ano_para_validacao, mes, dia)

            _tipo = 'fixo'
        else:
            if func is None:
                raise ValueError("'func' é obrigatório se 'mes' e 'dia' forem ambos None")
            if not callable(func):
                raise TypeError("'func' deve ser uma função")
            _tipo = 'dinamico'

        self.mes = mes
        self.dia = dia
        self.func = func
        self.ano_inicio = ano_inicio
        self.ano_fim = ano_fim
        self._tipo = _tipo

    def calc_para_ano(self, ano: int) -> datetime.date | None:
        """
        Calcula a data exata do feriado para o ano especificado.

        Parâmetros
        ----------
        ano : int
            O ano para calcular a data do feriado.

        Retorna
        -------
        datetime.date
            A data do feriado para o ano especificado.
        """
        # Apenas para validar o valor do ano.
        # Valores como -5 ou 60000 são inválidos.
        datetime.date(ano, 1, 1)

        if self._tipo == 'fixo':
            if self.ano_inicio is not None and ano < self.ano_inicio:
                return None
            if self.ano_fim is not None and ano > self.ano_fim:
                return None
            return datetime.date(ano, self.mes, self.dia)  # type: ignore
        else:
            resposta_func = self.func(ano)  # type: ignore
            if not isinstance(resposta_func, datetime.date):
                raise TypeError("'func' deve retornar um datetime.date")
            return resposta_func

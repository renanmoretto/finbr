"""Variação acumulada e correção de valores por índices do SGS (IPCA, IGP-M, INPC, CDI, SELIC).

Convenções (as mesmas da Calculadora do Cidadão do Banco Central):
- índices mensais: do mês de `inicio` ao mês de `fim`, ambos inclusive;
- índices diários: de `inicio` (inclusive) a `fim` (exclusive).
"""

from __future__ import annotations

import datetime
import logging

import pandas as pd

from . import sgs

logger = logging.getLogger(__name__)

INDICES: dict[str, tuple[int, str]] = {
    'ipca': (433, 'mensal'),
    'igpm': (189, 'mensal'),
    'inpc': (188, 'mensal'),
    'cdi': (12, 'diario'),
    'selic': (11, 'diario'),
}


def _data(valor: datetime.date | str | None) -> datetime.date | None:
    if isinstance(valor, str):
        return datetime.date.fromisoformat(valor)
    return valor


def _meses_atras(data: datetime.date, meses: int) -> datetime.date:
    total = data.year * 12 + (data.month - 1) - meses
    return datetime.date(total // 12, total % 12 + 1, 1)


def _um_ano_antes(data: datetime.date) -> datetime.date:
    try:
        return data.replace(year=data.year - 1)
    except ValueError:
        return data.replace(year=data.year - 1, day=28)


def taxas(
    indice: str,
    inicio: datetime.date | str | None = None,
    fim: datetime.date | str | None = None,
) -> pd.Series:
    """Taxas por período (em decimal) que entram no acumulado entre `inicio` e `fim`.

    Sem `inicio`, usa os últimos 12 meses terminando em `fim`. Sem `fim`, usa hoje.
    """
    indice = indice.lower()
    if indice not in INDICES:
        raise ValueError(f'índice inválido: {indice!r}. Disponíveis: {", ".join(INDICES)}')
    codigo, frequencia = INDICES[indice]

    inicio = _data(inicio)
    fim = _data(fim) or datetime.date.today()
    if inicio is not None and inicio > fim:
        raise ValueError(f'início ({inicio}) depois do fim ({fim})')

    if frequencia == 'mensal':
        fim_consulta = fim.replace(day=1)
        # sem início: sobra de dois meses, o índice do mês anterior só sai por volta do dia 10
        inicio_consulta = inicio.replace(day=1) if inicio else _meses_atras(fim, 13)
    else:
        fim_consulta = fim - datetime.timedelta(days=1)
        inicio_consulta = inicio or _um_ano_antes(fim)
        if inicio_consulta > fim_consulta:
            raise ValueError(f'período vazio: {inicio_consulta} a {fim} (fim é exclusivo)')

    serie = sgs.get(codigo, inicio_consulta, fim_consulta)[codigo].dropna() / 100
    serie = serie[(serie.index.date >= inicio_consulta) & (serie.index.date <= fim_consulta)]
    if frequencia == 'mensal' and inicio is None:
        serie = serie.tail(12)
    if serie.empty:
        raise ValueError(f'sem dados de {indice} entre {inicio_consulta} e {fim_consulta}')

    serie.name = indice
    logger.debug(
        '%s: %d períodos de %s a %s',
        indice,
        len(serie),
        serie.index[0].date(),
        serie.index[-1].date(),
    )
    return serie


def acumulado(
    indice: str,
    inicio: datetime.date | str | None = None,
    fim: datetime.date | str | None = None,
) -> float:
    """Variação acumulada do índice no período (decimal). Sem `inicio`: últimos 12 meses."""
    return float((1 + taxas(indice, inicio, fim)).prod() - 1)


def corrigir(
    valor: float,
    indice: str,
    inicio: datetime.date | str,
    fim: datetime.date | str | None = None,
) -> dict:
    """Corrige `valor` pelo índice e devolve o resultado com o período efetivamente usado."""
    serie = taxas(indice, inicio, fim)
    fator = float((1 + serie).prod())
    return {
        'indice': indice.lower(),
        'de': serie.index[0].date(),
        'ate': serie.index[-1].date(),
        'periodos': len(serie),
        'fator': round(fator, 8),
        'variacao': round(fator - 1, 6),
        'valor_inicial': valor,
        'valor_corrigido': round(valor * fator, 2),
    }

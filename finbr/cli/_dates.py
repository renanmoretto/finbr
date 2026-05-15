"""Parser flexível de datas para a CLI.

Aceita:
    YYYY-MM-DD             -> data ISO
    today, hoje            -> data de hoje
    yesterday, ontem       -> data de ontem
    -5d, -2w, -3m, -1y     -> offset relativo à data de hoje
"""

from __future__ import annotations

import datetime
import re

import typer


_OFFSET_RE = re.compile(r'^-(\d+)([dwmy])$', re.IGNORECASE)


def parse_date(value: str | None) -> datetime.date | None:
    """Converte string para datetime.date. Retorna None se value for None."""
    if value is None:
        return None

    s = value.strip().lower()

    if s in {'today', 'hoje'}:
        return datetime.date.today()
    if s in {'yesterday', 'ontem'}:
        return datetime.date.today() - datetime.timedelta(days=1)

    m = _OFFSET_RE.match(s)
    if m:
        n = int(m.group(1))
        unit = m.group(2).lower()
        today = datetime.date.today()
        if unit == 'd':
            return today - datetime.timedelta(days=n)
        if unit == 'w':
            return today - datetime.timedelta(weeks=n)
        if unit == 'm':
            # mês aproximado: 30 dias
            return today - datetime.timedelta(days=n * 30)
        if unit == 'y':
            try:
                return today.replace(year=today.year - n)
            except ValueError:
                return today - datetime.timedelta(days=n * 365)

    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        raise typer.BadParameter(
            f"data inválida: {value!r}. Use YYYY-MM-DD, 'today', 'ontem', ou offsets como '-5d', '-2w', '-1m', '-1y'."
        )


def parse_date_required(value: str) -> datetime.date:
    """Igual a parse_date mas levanta se for None."""
    out = parse_date(value)
    if out is None:
        raise typer.BadParameter('data é obrigatória')
    return out

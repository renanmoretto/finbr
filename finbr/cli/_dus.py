"""Comandos `finbr dus ...` — utilitários de dias úteis (calendário B3)."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Optional

import typer

from .. import dias_uteis
from ._dates import parse_date
from ._output import Format, emit

app = typer.Typer(no_args_is_help=True)


@app.command(help='Próximo dia útil.')
def proximo(data: Optional[str] = typer.Argument(None, help='Data de referência (default: hoje).')) -> None:
    typer.echo(dias_uteis.proximo(parse_date(data)).isoformat())


@app.command(help='Último dia útil anterior.')
def ultimo(data: Optional[str] = typer.Argument(None)) -> None:
    typer.echo(dias_uteis.ultimo(parse_date(data)).isoformat())


@app.command(help='Aplica um delta em dias úteis (positivo ou negativo).')
def delta(
    data: str = typer.Argument(..., help='Data base.'),
    dias: int = typer.Option(..., '--dias', '-n', help='Quantidade de dias úteis (negativo para passado).'),
) -> None:
    typer.echo(dias_uteis.delta(parse_date(data), dias).isoformat())  # type: ignore[arg-type]


@app.command(help='Diferença em dias úteis entre duas datas.')
def dif(
    a: str = typer.Argument(...),
    b: str = typer.Argument(...),
) -> None:
    typer.echo(dias_uteis.dif(parse_date(a), parse_date(b)))  # type: ignore[arg-type]


@app.command('eh-util', help='Verifica se a data é dia útil.')
def eh_util(data: str = typer.Argument(...)) -> None:
    d = parse_date(data)
    assert d is not None
    typer.echo('sim' if dias_uteis.dia_util(d) else 'não')


@app.command(help='Lista todos os feriados do ano.')
def feriados(
    ano: Optional[int] = typer.Argument(None, help='Ano (default: ano atual).'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    y = ano or datetime.date.today().year
    feriados_ = [d.isoformat() for d in dias_uteis.feriados_ano(y)]
    emit([{'data': d} for d in feriados_], fmt=fmt, output=output, title=f'Feriados {y}')

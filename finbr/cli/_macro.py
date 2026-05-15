"""Comandos `finbr macro ...`."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .. import cdi as _cdi
from .. import ipca as _ipca
from .. import selic as _selic
from .. import sgs as _sgs
from ._dates import parse_date
from ._output import Format, emit

app = typer.Typer(no_args_is_help=True)


@app.command(help='Taxa CDI atual.')
def cdi(
    ao_ano: bool = typer.Option(True, '--ao-ano/--diario', help='Anualizada (default) ou diária.'),
) -> None:
    typer.echo(_cdi(ao_ano=ao_ano))


@app.command(help='Taxa SELIC atual.')
def selic(
    ao_ano: bool = typer.Option(True, '--ao-ano/--diaria'),
) -> None:
    typer.echo(_selic(ao_ano=ao_ano))


@app.command(help='IPCA mensal (histórico).')
def ipca(
    since: Optional[str] = typer.Option(None, '--since', help='Data inicial.'),
    until: Optional[str] = typer.Option(None, '--until', help='Data final.'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    inicio = parse_date(since)
    fim = parse_date(until)
    df = _ipca(
        start=inicio.isoformat() if inicio else None,
        end=fim.isoformat() if fim else None,
    )
    emit(df, fmt=fmt, output=output, title='IPCA mensal')


@app.command(help='Série temporal qualquer do SGS (Banco Central) por código.')
def serie(
    codigo: int = typer.Argument(..., help='Código da série no SGS, ex. 12 (CDI), 433 (IPCA).'),
    since: Optional[str] = typer.Option(None, '--since'),
    until: Optional[str] = typer.Option(None, '--until'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    df = _sgs.get(codigo, data_inicio=parse_date(since), data_fim=parse_date(until))
    emit(df, fmt=fmt, output=output, title=f'SGS {codigo}')


@app.command(help='Buscar séries do SGS por palavra-chave ou código.')
def buscar(
    query: str = typer.Argument(..., help='Texto ou código numérico.'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    q: int | str = int(query) if query.isdigit() else query
    data = _sgs.pesquisar(q)
    emit(data, fmt=fmt, output=output, title=f'SGS — busca: {query}')


@app.command(help='Metadados de uma série do SGS.')
def info(
    codigo: int = typer.Argument(...),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    data = _sgs.metadata(codigo)
    emit(data, fmt=fmt, output=output, title=f'SGS {codigo} — metadata')

"""Comandos `finbr b3 ...` — endpoints diretos da B3."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..b3 import cotahist as _cotahist
from ..b3 import plantao_noticias
from ._dates import parse_date, parse_date_required
from ._output import Format, emit

app = typer.Typer(no_args_is_help=True)

cotahist_app = typer.Typer(no_args_is_help=True, help='Cotações históricas (arquivos COTAHIST da B3).')
app.add_typer(cotahist_app, name='cotahist')


@cotahist_app.command('dia', help='COTAHIST de um pregão específico.')
def cotahist_dia(
    data: str = typer.Argument(..., help='Data do pregão (YYYY-MM-DD, today, -1d...).'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    d = parse_date_required(data)
    df = _cotahist.get(d)
    emit(df, fmt=fmt, output=output, title=f'COTAHIST {d.isoformat()}')


@cotahist_app.command('ano', help='COTAHIST anual.')
def cotahist_ano(
    ano: int = typer.Argument(..., help='Ano, ex. 2024.'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    df = _cotahist.get_ano(ano)
    emit(df, fmt=fmt, output=output, title=f'COTAHIST {ano}')


@app.command('noticias', help='Plantão de notícias da B3.')
def noticias(
    since: Optional[str] = typer.Option(None, '--since', help='Data inicial (default: hoje).'),
    until: Optional[str] = typer.Option(None, '--until', help='Data final (default: hoje).'),
    ticker: Optional[str] = typer.Option(None, '--ticker', help='Filtra por ticker.'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    items = plantao_noticias.get(parse_date(since), parse_date(until))
    rows = [
        {
            'data_hora': n.data_hora,
            'ticker': n.ticker,
            'empresa': n.empresa,
            'titulo': n.titulo.strip(),
            'url': n.url,
        }
        for n in items
    ]
    if ticker:
        rows = [r for r in rows if r['ticker'].upper() == ticker.upper()]
    emit(rows, fmt=fmt, output=output, title='B3 — plantão de notícias')

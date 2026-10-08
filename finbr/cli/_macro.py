"""Comandos `finbr macro ...`."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .. import cdi as _cdi
from .. import correcao as _correcao
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


_INDICES = ' | '.join(_correcao.INDICES)


@app.command(help=f'Variação acumulada de um índice ({_INDICES}). Default: últimos 12 meses.')
def acumulado(
    indice: str = typer.Argument(..., help=_INDICES),
    de: Optional[str] = typer.Option(None, '--de', help='Início (YYYY-MM ou data).'),
    ate: Optional[str] = typer.Option(None, '--ate', help='Fim (default: hoje).'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    try:
        taxas = _correcao.taxas(indice, parse_date(de), parse_date(ate))
    except ValueError as e:
        raise typer.BadParameter(str(e))
    data = {
        'indice': indice.lower(),
        'de': taxas.index[0].date(),
        'ate': taxas.index[-1].date(),
        'periodos': len(taxas),
        'variacao': round(float((1 + taxas).prod() - 1), 6),
    }
    emit(data, fmt=fmt, output=output, title=f'{indice.upper()} acumulado')


@app.command(help=f'Corrige um valor por um índice ({_INDICES}).')
def corrigir(
    valor: float = typer.Argument(..., help='Valor a corrigir, ex. 1000.'),
    de: str = typer.Option(..., '--de', help='Início (YYYY-MM ou data).'),
    ate: Optional[str] = typer.Option(None, '--ate', help='Fim (default: hoje).'),
    indice: str = typer.Option('ipca', '--indice', '-i', help=_INDICES),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    try:
        data = _correcao.corrigir(valor, indice, parse_date(de), parse_date(ate))
    except ValueError as e:
        raise typer.BadParameter(str(e))
    emit(data, fmt=fmt, output=output, title=f'Correção por {indice.upper()}')

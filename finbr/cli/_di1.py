"""Comandos `finbr di1 <ticker> <verbo>`."""

from __future__ import annotations

from typing import Optional

import typer

from ..b3 import di1
from ._dates import parse_date

app = typer.Typer(no_args_is_help=True)


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    ticker: Optional[str] = typer.Argument(None, help='Ticker DI1, ex. DI1F26.'),
) -> None:
    if ticker is None:
        if ctx.invoked_subcommand is None:
            typer.echo(ctx.get_help())
            raise typer.Exit()
        ctx.obj = {'ticker': None}
        return
    ctx.obj = {'ticker': ticker.upper()}
    if ctx.invoked_subcommand is None:
        # default: vencimento
        typer.echo(di1.vencimento(ticker.upper()).isoformat())


def _t(ctx: typer.Context) -> str:
    obj = ctx.obj or {}
    t = obj.get('ticker')
    if not t:
        raise typer.BadParameter('ticker é obrigatório (use `finbr di1 <TICKER> <verbo>`)')
    return t


@app.command(help='Data de vencimento do contrato DI1.')
def vencimento(ctx: typer.Context) -> None:
    typer.echo(di1.vencimento(_t(ctx)).isoformat())


@app.command(help='Dias até o vencimento.')
def dias(
    ctx: typer.Context,
    data: Optional[str] = typer.Option(None, '--data', help='Data de referência.'),
    corridos: bool = typer.Option(False, '--corridos', help='Dias corridos (default: úteis).'),
) -> None:
    typer.echo(di1.dias_vencimento(_t(ctx), parse_date(data), dias_uteis=not corridos))


@app.command(help='Calcula a taxa a partir do PU.')
def taxa(
    ctx: typer.Context,
    pu: float = typer.Argument(..., help='Preço unitário.'),
    data: Optional[str] = typer.Option(None, '--data'),
) -> None:
    typer.echo(di1.taxa(_t(ctx), pu, parse_date(data)))


@app.command(help='Calcula o PU a partir da taxa.')
def pu(
    ctx: typer.Context,
    taxa: float = typer.Argument(..., help='Taxa em decimal (ex. 0.12 para 12%).'),
    data: Optional[str] = typer.Option(None, '--data'),
) -> None:
    typer.echo(di1.preco_unitario(_t(ctx), taxa, parse_date(data)))


@app.command(help='DV01 do contrato.')
def dv01(
    ctx: typer.Context,
    taxa: float = typer.Argument(...),
    data: Optional[str] = typer.Option(None, '--data'),
) -> None:
    typer.echo(di1.dv01(_t(ctx), taxa, parse_date(data)))

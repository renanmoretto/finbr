"""Comandos `finbr acao <ticker> <verbo>`.

O ticker é passado uma única vez no nível do grupo e propagado aos subcomandos
via `ctx.obj`. Isso permite a UX natural: `finbr acao PETR4 dividendos`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .. import _yf, fundamentus
from ..statusinvest import acao as si_acao
from ._dates import parse_date
from ._output import Format, emit

app = typer.Typer(no_args_is_help=True)


def _ticker(ctx: typer.Context) -> str:
    return ctx.obj['ticker']


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    ticker: Optional[str] = typer.Argument(None, help='Ticker da ação, ex. PETR4.'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f', help='Formato de saída.'),
    output: Optional[Path] = typer.Option(None, '--output', '-o', help='Salvar em arquivo.'),
) -> None:
    """Sem verbo: resumo da ação. Com verbo: roteia para subcomando."""
    if ticker is None:
        if ctx.invoked_subcommand is None:
            typer.echo(ctx.get_help())
            raise typer.Exit()
        # subcomando sem ticker: deixa o subcomando reclamar
        ctx.obj = {'ticker': None, 'fmt': fmt, 'output': output}
        return

    ctx.obj = {'ticker': ticker.upper(), 'fmt': fmt, 'output': output}

    if ctx.invoked_subcommand is None:
        data = si_acao.detalhes(ticker.upper())
        emit(data, fmt=fmt, output=output, title=f'{ticker.upper()} — resumo')


def _resolve(ctx: typer.Context, fmt: Format, output: Optional[Path]) -> tuple[str, Format, Optional[Path]]:
    """Combina ticker do grupo com flags do subcomando.

    Se o subcomando passou --format/--output explicitamente, esses ganham.
    Se não, herda do grupo.
    """
    obj = ctx.obj or {}
    ticker = obj.get('ticker')
    if not ticker:
        raise typer.BadParameter('ticker é obrigatório (use `finbr acao <TICKER> <verbo>`)')
    final_fmt = fmt if fmt != Format.auto else obj.get('fmt', Format.auto)
    final_out = output if output is not None else obj.get('output')
    return ticker, final_fmt, final_out


@app.command(help='Detalhes / dados gerais da empresa.')
def info(
    ctx: typer.Context,
    fonte: str = typer.Option('statusinvest', '--fonte', help='statusinvest | fundamentus'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    ticker, fmt, output = _resolve(ctx, fmt, output)
    if fonte == 'fundamentus':
        data = fundamentus.detalhes(ticker)
    else:
        data = si_acao.detalhes(ticker)
    emit(data, fmt=fmt, output=output, title=f'{ticker} — info')


@app.command(help='Múltiplos / indicadores históricos.')
def multiplos(
    ctx: typer.Context,
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    ticker, fmt, output = _resolve(ctx, fmt, output)
    data = si_acao.multiplos(ticker)
    emit(data, fmt=fmt, output=output, title=f'{ticker} — múltiplos')


@app.command(help='Dividendos pagos.')
def dividendos(
    ctx: typer.Context,
    fonte: str = typer.Option('statusinvest', '--fonte', help='statusinvest | fundamentus'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    ticker, fmt, output = _resolve(ctx, fmt, output)
    if fonte == 'fundamentus':
        data = fundamentus.proventos(ticker)
    else:
        data = si_acao.dividendos(ticker)
    emit(data, fmt=fmt, output=output, title=f'{ticker} — dividendos')


@app.command(help='Demonstração de resultados (DRE).')
def resultados(
    ctx: typer.Context,
    periodo: str = typer.Option('trimestral', '--periodo', help='trimestral | anual'),
    ano_inicio: Optional[int] = typer.Option(None, '--ano-inicio'),
    ano_fim: Optional[int] = typer.Option(None, '--ano-fim'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    ticker, fmt, output = _resolve(ctx, fmt, output)
    data = si_acao.resultados(ticker, ano_inicio, ano_fim, periodo)  # type: ignore[arg-type]
    emit(data, fmt=fmt, output=output, title=f'{ticker} — resultados ({periodo})')


@app.command(help='Balanço patrimonial.')
def balanco(
    ctx: typer.Context,
    periodo: str = typer.Option('trimestral', '--periodo'),
    ano_inicio: Optional[int] = typer.Option(None, '--ano-inicio'),
    ano_fim: Optional[int] = typer.Option(None, '--ano-fim'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    ticker, fmt, output = _resolve(ctx, fmt, output)
    data = si_acao.balanco(ticker, ano_inicio, ano_fim, periodo)  # type: ignore[arg-type]
    emit(data, fmt=fmt, output=output, title=f'{ticker} — balanço ({periodo})')


@app.command(help='Fluxo de caixa.')
def fluxo(
    ctx: typer.Context,
    periodo: str = typer.Option('trimestral', '--periodo'),
    ano_inicio: Optional[int] = typer.Option(None, '--ano-inicio'),
    ano_fim: Optional[int] = typer.Option(None, '--ano-fim'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    ticker, fmt, output = _resolve(ctx, fmt, output)
    data = si_acao.fluxo_de_caixa(ticker, ano_inicio, ano_fim, periodo)  # type: ignore[arg-type]
    emit(data, fmt=fmt, output=output, title=f'{ticker} — fluxo de caixa ({periodo})')


@app.command(help='Histórico de preços (Yahoo Finance).')
def precos(
    ctx: typer.Context,
    since: Optional[str] = typer.Option(None, '--since', help='Data inicial.'),
    until: Optional[str] = typer.Option(None, '--until', help='Data final.'),
    periodo: str = typer.Option('1y', '--periodo'),
    intervalo: str = typer.Option('1d', '--intervalo'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    ticker, fmt, output = _resolve(ctx, fmt, output)
    inicio = parse_date(since)
    fim = parse_date(until)
    df = _yf.precos(
        ticker,
        periodo=periodo if inicio is None else 'max',
        intervalo=intervalo,
        data_inicio=inicio,
        data_fim=fim,
    )
    emit(df, fmt=fmt, output=output, title=f'{ticker} — preços')


@app.command(help='Resultados trimestrais (links CVM).')
def trimestrais(
    ctx: typer.Context,
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    ticker, fmt, output = _resolve(ctx, fmt, output)
    data = fundamentus.resultados_trimestrais(ticker)
    emit(data, fmt=fmt, output=output, title=f'{ticker} — resultados trimestrais')


@app.command(help='Apresentações ao investidor (links).')
def apresentacoes(
    ctx: typer.Context,
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    ticker, fmt, output = _resolve(ctx, fmt, output)
    data = fundamentus.apresentacoes(ticker)
    emit(data, fmt=fmt, output=output, title=f'{ticker} — apresentações')

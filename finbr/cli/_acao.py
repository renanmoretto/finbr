"""Comandos `finbr acao <ticker> <verbo>`.

O ticker é passado uma única vez no nível do grupo e propagado aos subcomandos
via `ctx.obj`. Isso permite a UX natural: `finbr acao PETR4 dividendos`.

Vários tickers vão separados por vírgula (`finbr acao PETR4,VALE3 precos`): o grupo
não aceita lista separada por espaço porque o token seguinte é o verbo.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import typer

from .. import _yf, fundamentus
from ..statusinvest import acao as si_acao
from ._dates import parse_date
from ._output import Format, emit

logger = logging.getLogger(__name__)

app = typer.Typer(no_args_is_help=True)

_COLUNAS_ID = ['companyid', 'segmentid', 'sectorid', 'subsectorid']
_OHLCV = ['Open', 'High', 'Low', 'Close', 'Volume']


def _parse_tickers(valores: list[str]) -> list[str]:
    tickers = [t.strip().upper() for v in valores for t in v.split(',') if t.strip()]
    return list(dict.fromkeys(tickers))


def comparacao(tickers: list[str], campos: str | None = None) -> pd.DataFrame:
    """Indicadores lado a lado: uma linha por campo, uma coluna por ticker."""
    df = pd.DataFrame(si_acao.screener()).set_index('ticker').drop(columns=_COLUNAS_ID)
    logger.debug('comparacao: %d tickers no screener, pedidos %s', len(df), tickers)

    faltando = [t for t in tickers if t not in df.index]
    if faltando:
        raise typer.BadParameter(f'ticker(s) não encontrado(s): {", ".join(faltando)}')

    if campos is not None:
        selecionados = [c.strip() for c in campos.split(',') if c.strip()]
        invalidos = [c for c in selecionados if c not in df.columns]
        if invalidos:
            raise typer.BadParameter(
                f'campo(s) inexistente(s): {", ".join(invalidos)}. '
                f'Disponíveis: {", ".join(df.columns)}'
            )
        df = df[selecionados]

    out = df.loc[tickers].T
    out.columns.name = None
    return out.rename_axis('campo').reset_index()


def tabela_precos(df: pd.DataFrame, tickers: list[str], campo: str = 'Close') -> pd.DataFrame:
    """Achata o retorno do Yahoo: OHLCV para um ticker, um campo por ticker para vários."""
    if df.empty:
        raise typer.BadParameter(f'sem preços para: {", ".join(tickers)}')

    if len(tickers) == 1:
        out = df.droplevel(1, axis=1) if isinstance(df.columns, pd.MultiIndex) else df
        ohlcv = [c for c in _OHLCV if c in out.columns]
        out = out[ohlcv + [c for c in out.columns if c not in ohlcv]]
    else:
        campos = list(dict.fromkeys(df.columns.get_level_values(0)))
        escolhido = next((c for c in campos if c.lower() == campo.lower()), None)
        if escolhido is None:
            raise typer.BadParameter(f'campo inválido: {campo!r}. Disponíveis: {", ".join(campos)}')
        out = df[escolhido]
        sem_dados = [t for t in tickers if t not in out.columns or out[t].isna().all()]
        if sem_dados:
            raise typer.BadParameter(f'sem preços para: {", ".join(sem_dados)}')
        out = out[tickers]

    out = out.copy()
    out.columns.name = None
    return out


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    ticker: Optional[str] = typer.Argument(
        None, help='Ticker da ação, ex. PETR4. Vários separados por vírgula: PETR4,VALE3.'
    ),
    fmt: Format = typer.Option(Format.auto, '--format', '-f', help='Formato de saída.'),
    output: Optional[Path] = typer.Option(None, '--output', '-o', help='Salvar em arquivo.'),
) -> None:
    """Sem verbo: resumo da ação. Com verbo: roteia para subcomando."""
    if ticker is None:
        if ctx.invoked_subcommand is None:
            typer.echo(ctx.get_help())
            raise typer.Exit()
        # subcomando sem ticker: deixa o subcomando reclamar
        ctx.obj = {'tickers': [], 'fmt': fmt, 'output': output}
        return

    tickers = _parse_tickers([ticker])
    ctx.obj = {'tickers': tickers, 'fmt': fmt, 'output': output}

    if ctx.invoked_subcommand is None:
        if len(tickers) > 1:
            emit(comparacao(tickers), fmt=fmt, output=output, title=' x '.join(tickers))
            return
        data = si_acao.detalhes(tickers[0])
        emit(data, fmt=fmt, output=output, title=f'{tickers[0]} — resumo')


def _resolve_multi(
    ctx: typer.Context, fmt: Format, output: Optional[Path]
) -> tuple[list[str], Format, Optional[Path]]:
    """Combina tickers do grupo com flags do subcomando.

    Se o subcomando passou --format/--output explicitamente, esses ganham.
    Se não, herda do grupo.
    """
    obj = ctx.obj or {}
    tickers = obj.get('tickers')
    if not tickers:
        raise typer.BadParameter('ticker é obrigatório (use `finbr acao <TICKER> <verbo>`)')
    final_fmt = fmt if fmt != Format.auto else obj.get('fmt', Format.auto)
    final_out = output if output is not None else obj.get('output')
    return tickers, final_fmt, final_out


def _resolve(
    ctx: typer.Context, fmt: Format, output: Optional[Path]
) -> tuple[str, Format, Optional[Path]]:
    tickers, final_fmt, final_out = _resolve_multi(ctx, fmt, output)
    if len(tickers) > 1:
        raise typer.BadParameter(
            f'`{ctx.info_name}` aceita um ticker só; vários tickers valem para `precos` '
            'e para `finbr comparar`'
        )
    return tickers[0], final_fmt, final_out


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


@app.command(help='Histórico de preços (Yahoo Finance). Aceita vários tickers: PETR4,VALE3.')
def precos(
    ctx: typer.Context,
    since: Optional[str] = typer.Option(None, '--since', help='Data inicial.'),
    until: Optional[str] = typer.Option(None, '--until', help='Data final.'),
    periodo: str = typer.Option('1y', '--periodo'),
    intervalo: str = typer.Option('1d', '--intervalo'),
    campo: str = typer.Option(
        'Close', '--campo', help='Com vários tickers: Open | High | Low | Close | Volume.'
    ),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    tickers, fmt, output = _resolve_multi(ctx, fmt, output)
    inicio = parse_date(since)
    fim = parse_date(until)
    df = _yf.precos(
        tickers,
        periodo=periodo if inicio is None else 'max',
        intervalo=intervalo,
        data_inicio=inicio,
        data_fim=fim,
    )
    logger.debug('precos: %d linhas para %s', len(df), tickers)
    emit(
        tabela_precos(df, tickers, campo),
        fmt=fmt,
        output=output,
        title=f'{", ".join(tickers)} — preços',
    )


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


def comparar(
    tickers: list[str] = typer.Argument(..., help='Tickers, ex. PETR4 VALE3 ITUB4.'),
    campos: Optional[str] = typer.Option(
        None, '--campos', '-c', help='Campos a comparar, separados por vírgula.'
    ),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    lista = _parse_tickers(tickers)
    emit(comparacao(lista, campos), fmt=fmt, output=output, title=' x '.join(lista))

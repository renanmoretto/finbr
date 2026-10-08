"""Comando `finbr screener`."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import typer

from ..statusinvest import acao as si_acao
from ._output import Format, _resolve_format, emit

logger = logging.getLogger(__name__)


def _checa_colunas(df: pd.DataFrame, colunas: list[str], flag: str) -> None:
    faltando = [c for c in colunas if c not in df.columns]
    if faltando:
        raise typer.BadParameter(
            f'coluna(s) inexistente(s) em {flag}: {", ".join(faltando)}. '
            f'Disponíveis: {", ".join(df.columns)}'
        )


def filtrar(
    data: list[dict],
    where: list[str] | None = None,
    sort: str | None = None,
    desc: bool = False,
    colunas: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    df = pd.DataFrame(data)
    logger.debug('screener: %d linhas antes dos filtros', len(df))

    for expr in where or []:
        try:
            df = df.query(expr)
        except Exception as e:
            raise typer.BadParameter(
                f'filtro inválido em --where {expr!r}: {e}. Disponíveis: {", ".join(df.columns)}'
            )
        logger.debug('screener: %d linhas após --where %r', len(df), expr)

    if sort is not None:
        _checa_colunas(df, [sort], '--sort')
        df = df.sort_values(sort, ascending=not desc, na_position='last')

    if colunas is not None:
        selecionadas = [c.strip() for c in colunas.split(',') if c.strip()]
        _checa_colunas(df, selecionadas, '--colunas')
        df = df[selecionadas]

    if limit is not None:
        df = df.head(limit)

    return df.reset_index(drop=True)


def screener(
    where: Optional[list[str]] = typer.Option(
        None,
        '--where',
        '-w',
        help='Filtro, ex. "p_l < 10 and dy > 6". Pode repetir (combinados com AND).',
    ),
    sort: Optional[str] = typer.Option(None, '--sort', '-s', help='Coluna para ordenar.'),
    desc: bool = typer.Option(False, '--desc', help='Ordem decrescente.'),
    colunas: Optional[str] = typer.Option(
        None, '--colunas', '-c', help='Colunas a exibir, separadas por vírgula.'
    ),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
    limit: Optional[int] = typer.Option(
        None, '--limit', '-n', help='Limita N primeiros resultados.'
    ),
) -> None:
    data = si_acao.screener()
    df = filtrar(data, where=where, sort=sort, desc=desc, colunas=colunas, limit=limit)
    if _resolve_format(fmt, output) == Format.json:
        # JSON omite campos ausentes em vez de emitir NaN (inválido em JSON)
        registros = [
            {k: v for k, v in linha.items() if pd.notna(v)} for linha in df.to_dict('records')
        ]
        emit(registros, fmt=fmt, output=output, title='Screener')
        return
    emit(df, fmt=fmt, output=output, title='Screener')

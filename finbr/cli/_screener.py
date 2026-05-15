"""Comando `finbr screener`."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..statusinvest import acao as si_acao
from ._output import Format, emit


def screener(
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
    limit: Optional[int] = typer.Option(None, '--limit', '-n', help='Limita N primeiros resultados.'),
) -> None:
    data = si_acao.screener()
    if limit is not None:
        data = data[:limit]
    emit(data, fmt=fmt, output=output, title='Screener')

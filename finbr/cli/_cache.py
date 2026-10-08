"""Comandos `finbr cache ...` — cache em disco dos downloads."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .. import _cache
from ._output import Format, emit

app = typer.Typer(no_args_is_help=True)


@app.command(help='Onde está o cache e quanto ocupa.')
def info(
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    emit(_cache.info(), fmt=fmt, output=output, title='Cache')


@app.command(help='Apaga todos os arquivos em cache.')
def limpar() -> None:
    typer.echo(f'{_cache.limpar()} arquivo(s) removido(s) de {_cache.diretorio()}')

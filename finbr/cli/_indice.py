"""Comandos `finbr indice <nome> ...`."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..b3 import indices
from ._output import Format, emit

app = typer.Typer(no_args_is_help=True)


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    nome: Optional[str] = typer.Argument(None, help='Código do índice, ex. IBOV, SMLL, IDIV.'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    """Sem verbo: composição do índice."""
    if nome is None:
        if ctx.invoked_subcommand is None:
            typer.echo(ctx.get_help())
            raise typer.Exit()
        ctx.obj = {'nome': None, 'fmt': fmt, 'output': output}
        return

    ctx.obj = {'nome': nome.upper(), 'fmt': fmt, 'output': output}

    if ctx.invoked_subcommand is None:
        df = indices.composicao(nome.upper())
        emit(df, fmt=fmt, output=output, title=f'{nome.upper()} — composição')


def _resolve(ctx: typer.Context, fmt: Format, output: Optional[Path]) -> tuple[str, Format, Optional[Path]]:
    obj = ctx.obj or {}
    nome = obj.get('nome')
    if not nome:
        raise typer.BadParameter('índice é obrigatório (use `finbr indice <NOME> <verbo>`)')
    final_fmt = fmt if fmt != Format.auto else obj.get('fmt', Format.auto)
    final_out = output if output is not None else obj.get('output')
    return nome, final_fmt, final_out


@app.command(help='Preço histórico do índice.')
def precos(
    ctx: typer.Context,
    ano_inicio: Optional[int] = typer.Option(None, '--ano-inicio'),
    ano_fim: Optional[int] = typer.Option(None, '--ano-fim'),
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    nome, fmt, output = _resolve(ctx, fmt, output)
    df = indices.preco_historico(nome, ano_inicio, ano_fim)
    emit(df, fmt=fmt, output=output, title=f'{nome} — preço histórico')


@app.command(help='Composição atual do índice.')
def composicao(
    ctx: typer.Context,
    fmt: Format = typer.Option(Format.auto, '--format', '-f'),
    output: Optional[Path] = typer.Option(None, '--output', '-o'),
) -> None:
    nome, fmt, output = _resolve(ctx, fmt, output)
    df = indices.composicao(nome)
    emit(df, fmt=fmt, output=output, title=f'{nome} — composição')

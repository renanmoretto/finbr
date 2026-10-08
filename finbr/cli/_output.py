"""Helpers de output: format/print/save.

Princípios:
- Quando stdout é TTY e formato é 'auto', imprime tabela bonita (rich).
- Quando stdout não é TTY (pipe/redirect) e formato é 'auto', emite CSV (ou JSON para
  estruturas escalares) para ficar amigável a pipes.
- Se `--output/-o file` for passado, salva no arquivo (formato inferido da extensão).
"""

from __future__ import annotations

import json
import sys
from enum import Enum
from pathlib import Path
from typing import Any

import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)


class Format(str, Enum):
    auto = 'auto'
    table = 'table'
    json = 'json'
    csv = 'csv'
    parquet = 'parquet'


def _resolve_format(fmt: Format, output: Path | None) -> Format:
    """Resolve 'auto' baseado em TTY/extensão de arquivo."""
    if output is not None:
        ext = output.suffix.lower().lstrip('.')
        if ext in {'csv', 'tsv'}:
            return Format.csv
        if ext == 'json':
            return Format.json
        if ext in {'parquet', 'pq'}:
            return Format.parquet
        # outras extensões -> csv por padrão
        return Format.csv

    if fmt != Format.auto:
        return fmt

    return Format.table if sys.stdout.isatty() else Format.csv


def _to_dataframe(data: Any) -> pd.DataFrame:
    """Normaliza payloads variados para DataFrame quando possível."""
    if isinstance(data, pd.DataFrame):
        return data
    if isinstance(data, pd.Series):
        return data.to_frame()
    if isinstance(data, list):
        if len(data) == 0:
            return pd.DataFrame()
        if all(isinstance(x, dict) for x in data):
            return pd.DataFrame(data)
        return pd.DataFrame({'valor': data})
    if isinstance(data, dict):
        # dict simples key->value vira duas colunas
        if data and not any(isinstance(v, (dict, list)) for v in data.values()):
            return pd.DataFrame(
                {'campo': list(data.keys()), 'valor': list(data.values())}
            )
        return pd.DataFrame([data])
    return pd.DataFrame({'valor': [data]})


def _render_table(df: pd.DataFrame, title: str | None = None) -> None:
    if df.empty:
        console.print('[dim]sem resultados[/dim]')
        return

    table = Table(title=title, header_style='bold cyan', show_lines=False)

    # se o index não é o default RangeIndex, mostre-o
    show_index = not (
        isinstance(df.index, pd.RangeIndex)
        and df.index.start == 0
        and df.index.step == 1
    )

    if show_index:
        idx_name = df.index.name or ''
        table.add_column(str(idx_name), style='dim')

    for col in df.columns:
        table.add_column(str(col))

    for idx, row in df.iterrows():
        cells = []
        if show_index:
            cells.append(_fmt_cell(idx))
        for v in row.tolist():
            cells.append(_fmt_cell(v))
        table.add_row(*cells)

    console.print(table)


def _fmt_cell(v: Any) -> str:
    if v is None:
        return ''
    if isinstance(v, float):
        if pd.isna(v):
            return ''
        # heurística simples de formatação
        if abs(v) >= 1e9:
            return f'{v:,.0f}'
        if abs(v) >= 1:
            return f'{v:,.4f}'.rstrip('0').rstrip('.')
        return f'{v:.6f}'.rstrip('0').rstrip('.')
    return str(v)


def _default_json(obj: Any) -> Any:
    import datetime as _dt

    if isinstance(obj, (_dt.date, _dt.datetime)):
        return obj.isoformat()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if hasattr(obj, 'item'):  # numpy scalars
        return obj.item()
    raise TypeError(f'não serializável: {type(obj)}')


def emit(
    data: Any,
    fmt: Format = Format.auto,
    output: Path | None = None,
    title: str | None = None,
) -> None:
    """Ponto único de saída — chama isto no fim de cada comando."""
    resolved = _resolve_format(fmt, output)

    # JSON: serializa diretamente (preserva estrutura aninhada)
    if resolved == Format.json:
        if isinstance(data, pd.DataFrame):
            sem_indice = isinstance(data.index, pd.RangeIndex)
            payload = data.reset_index(drop=sem_indice).to_dict(orient='records')
        elif isinstance(data, pd.Series):
            payload = data.reset_index().to_dict(orient='records')
        else:
            payload = data
        text = json.dumps(payload, ensure_ascii=False, indent=2, default=_default_json)
        if output is not None:
            output.write_text(text, encoding='utf-8')
        else:
            print(text)
        return

    df = _to_dataframe(data)

    if resolved == Format.csv:
        if output is not None:
            df.to_csv(output, index=isinstance(df.index, pd.DatetimeIndex))
        else:
            print(df.to_csv(index=isinstance(df.index, pd.DatetimeIndex)), end='')
        return

    if resolved == Format.parquet:
        if output is None:
            err_console.print('[red]parquet precisa de --output[/red]')
            raise SystemExit(2)
        # polars escreve parquet sem precisar de pyarrow
        import polars as pl

        # preservar o index se for DatetimeIndex
        if isinstance(df.index, pd.DatetimeIndex):
            df_to_write = df.reset_index()
        else:
            df_to_write = df
        pl.from_pandas(df_to_write).write_parquet(output)
        return

    # table
    _render_table(df, title=title)

"""CLI do finbr — dados do mercado financeiro brasileiro no terminal."""

from __future__ import annotations

import typer

from . import _acao, _b3, _di1, _dus, _indice, _macro, _screener

app = typer.Typer(
    name='finbr',
    help='finbr — dados do mercado financeiro brasileiro no terminal.',
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode='rich',
)

app.add_typer(_acao.app, name='acao', help='Dados de ações (preço, fundamentos, dividendos).')
app.add_typer(_indice.app, name='indice', help='Preços e composição de índices da B3.')
app.add_typer(_macro.app, name='macro', help='Indicadores macro (CDI, SELIC, IPCA, séries SGS).')
app.add_typer(_di1.app, name='di1', help='Contratos futuros de DI1.')
app.add_typer(_b3.app, name='b3', help='Dados direto da B3 (cotahist, notícias).')
app.add_typer(_dus.app, name='dus', help='Utilitários de dias úteis (calendário B3).')
app.command('screener', help='Screener de ações da B3.')(_screener.screener)
app.command('comparar', help='Compara indicadores de várias ações lado a lado.')(_acao.comparar)


if __name__ == '__main__':
    app()

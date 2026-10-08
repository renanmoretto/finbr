import json
import unittest
from unittest import mock

import typer
from typer.testing import CliRunner

from finbr.cli import app
from finbr.cli._screener import filtrar

DATA = [
    {'ticker': 'AAAA3', 'price': 10.0, 'p_l': 5.0, 'dy': 8.0, 'sectorname': 'Financeiro'},
    {'ticker': 'BBBB3', 'price': 20.0, 'p_l': 15.0, 'dy': 2.0, 'sectorname': 'Saúde'},
    {'ticker': 'CCCC3', 'price': 30.0, 'p_l': 8.0, 'sectorname': 'Financeiro'},
    {'ticker': 'DDDD3', 'price': 40.0, 'p_l': -3.0, 'dy': 12.0, 'sectorname': 'Saúde'},
]


class TestFiltrar(unittest.TestCase):
    def test_sem_filtros_mantem_tudo(self):
        df = filtrar(DATA)
        assert df['ticker'].tolist() == ['AAAA3', 'BBBB3', 'CCCC3', 'DDDD3']

    def test_where(self):
        df = filtrar(DATA, where=['p_l < 10 and dy > 6'])
        assert df['ticker'].tolist() == ['AAAA3', 'DDDD3']

    def test_where_repetido_combina_com_and(self):
        df = filtrar(DATA, where=['p_l > 0', 'p_l < 10'])
        assert df['ticker'].tolist() == ['AAAA3', 'CCCC3']

    def test_where_ignora_valores_ausentes(self):
        df = filtrar(DATA, where=['dy > 0'])
        assert 'CCCC3' not in df['ticker'].tolist()

    def test_where_texto(self):
        df = filtrar(DATA, where=['sectorname == "Saúde"'])
        assert df['ticker'].tolist() == ['BBBB3', 'DDDD3']

    def test_sort_asc_e_desc(self):
        assert filtrar(DATA, sort='p_l')['ticker'].tolist() == ['DDDD3', 'AAAA3', 'CCCC3', 'BBBB3']
        assert filtrar(DATA, sort='p_l', desc=True)['ticker'].tolist()[0] == 'BBBB3'

    def test_sort_ausentes_no_fim(self):
        assert filtrar(DATA, sort='dy', desc=True)['ticker'].tolist()[-1] == 'CCCC3'
        assert filtrar(DATA, sort='dy')['ticker'].tolist()[-1] == 'CCCC3'

    def test_colunas_e_limit(self):
        df = filtrar(DATA, sort='dy', desc=True, colunas='ticker, dy', limit=2)
        assert df.columns.tolist() == ['ticker', 'dy']
        assert df['ticker'].tolist() == ['DDDD3', 'AAAA3']

    def test_filtra_por_coluna_nao_exibida(self):
        df = filtrar(DATA, where=['p_l < 10'], sort='price', colunas='ticker')
        assert df.columns.tolist() == ['ticker']
        assert df['ticker'].tolist() == ['AAAA3', 'CCCC3', 'DDDD3']

    def test_erros(self):
        for kwargs in (
            {'where': ['nao_existe > 1']},
            {'where': ['p_l <<< 1']},
            {'sort': 'nao_existe'},
            {'colunas': 'ticker,nao_existe'},
        ):
            with self.assertRaises(typer.BadParameter):
                filtrar(DATA, **kwargs)


class TestScreenerCli(unittest.TestCase):
    def _run(self, *args):
        with mock.patch('finbr.statusinvest.acao.screener', return_value=DATA):
            return CliRunner().invoke(app, ['screener', *args])

    def test_csv(self):
        r = self._run(
            '-w', 'p_l < 10', '-w', 'dy > 6', '-s', 'dy', '--desc', '-c', 'ticker,dy', '-f', 'csv'
        )
        assert r.exit_code == 0, r.output
        assert r.output.splitlines() == ['ticker,dy', 'DDDD3,12.0', 'AAAA3,8.0']

    def test_sem_flags_exporta_tudo(self):
        r = self._run('-f', 'csv')
        assert r.exit_code == 0, r.output
        assert len(r.output.splitlines()) == len(DATA) + 1

    def test_json_valido_sem_nan_nem_index(self):
        r = self._run('-f', 'json')
        assert r.exit_code == 0, r.output
        registros = json.loads(r.output)
        assert registros == DATA

    def test_coluna_invalida(self):
        r = self._run('-w', 'xyz > 1')
        assert r.exit_code == 2
        assert 'xyz' in r.output

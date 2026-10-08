import json
import unittest
from unittest import mock

import pandas as pd
import typer
from typer.testing import CliRunner

from finbr.cli import app
from finbr.cli._acao import _parse_tickers, comparacao, tabela_precos

_IDS = {'companyid': 1, 'segmentid': 1, 'sectorid': 1, 'subsectorid': 1}
SCREENER = [
    {**_IDS, 'ticker': 'AAAA3', 'price': 10.0, 'p_l': 5.0, 'dy': 8.0, 'sectorname': 'Fin'},
    {**_IDS, 'ticker': 'BBBB3', 'price': 20.0, 'p_l': 15.0, 'sectorname': 'Saúde'},
    {**_IDS, 'ticker': 'CCCC3', 'price': 30.0, 'p_l': 8.0, 'dy': 1.0, 'sectorname': 'Fin'},
]

DATAS = pd.to_datetime(['2024-01-02', '2024-01-03'])
DATAS.name = 'Date'


def _yf_frame(tickers: list[str]) -> pd.DataFrame:
    campos = ['Close', 'High', 'Low', 'Open', 'Volume']
    colunas = pd.MultiIndex.from_product([campos, tickers], names=['Price', 'Ticker'])
    valores = [
        [float(i * 10 + j + linha) for i in range(len(campos)) for j in range(len(tickers))]
        for linha in range(len(DATAS))
    ]
    return pd.DataFrame(valores, index=DATAS, columns=colunas)


class TestParseTickers(unittest.TestCase):
    def test_virgula_espaco_caixa_e_duplicados(self):
        assert _parse_tickers(['petr4, vale3', 'ITUB4', 'PETR4']) == ['PETR4', 'VALE3', 'ITUB4']


class TestComparacao(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch('finbr.statusinvest.acao.screener', return_value=SCREENER)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_uma_coluna_por_ticker_na_ordem_pedida(self):
        df = comparacao(['CCCC3', 'AAAA3'])
        assert df.columns.tolist() == ['campo', 'CCCC3', 'AAAA3']
        assert 'companyid' not in df['campo'].tolist()
        linha = df.set_index('campo').loc['p_l']
        assert linha['CCCC3'] == 8.0 and linha['AAAA3'] == 5.0

    def test_campos(self):
        df = comparacao(['AAAA3', 'BBBB3'], campos='dy, price')
        assert df['campo'].tolist() == ['dy', 'price']
        assert pd.isna(df.set_index('campo').loc['dy', 'BBBB3'])

    def test_erros(self):
        with self.assertRaises(typer.BadParameter):
            comparacao(['AAAA3', 'ZZZZ3'])
        with self.assertRaises(typer.BadParameter):
            comparacao(['AAAA3'], campos='nao_existe')


class TestTabelaPrecos(unittest.TestCase):
    def test_um_ticker_vira_ohlcv_plano(self):
        df = tabela_precos(_yf_frame(['PETR4']), ['PETR4'])
        assert df.columns.tolist() == ['Open', 'High', 'Low', 'Close', 'Volume']
        assert df.columns.name is None
        assert df['Close'].tolist() == [0.0, 1.0]

    def test_varios_tickers_um_campo_na_ordem_pedida(self):
        df = tabela_precos(_yf_frame(['PETR4', 'VALE3']), ['VALE3', 'PETR4'])
        assert df.columns.tolist() == ['VALE3', 'PETR4']
        assert df['VALE3'].tolist() == [1.0, 2.0]

    def test_campo_case_insensitive(self):
        df = tabela_precos(_yf_frame(['PETR4', 'VALE3']), ['PETR4', 'VALE3'], campo='volume')
        assert df['PETR4'].tolist() == [40.0, 41.0]

    def test_erros(self):
        frame = _yf_frame(['PETR4', 'VALE3'])
        with self.assertRaises(typer.BadParameter):
            tabela_precos(frame, ['PETR4', 'VALE3'], campo='xyz')
        with self.assertRaises(typer.BadParameter):
            tabela_precos(frame.iloc[0:0], ['PETR4', 'VALE3'])
        frame[('Close', 'VALE3')] = float('nan')
        with self.assertRaises(typer.BadParameter) as ctx:
            tabela_precos(frame, ['PETR4', 'VALE3'])
        assert 'VALE3' in str(ctx.exception)


class TestAcaoCli(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        patcher = mock.patch('finbr.statusinvest.acao.screener', return_value=SCREENER)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_precos_varios(self):
        with mock.patch('finbr._yf.precos', return_value=_yf_frame(['PETR4', 'VALE3'])) as m:
            r = self.runner.invoke(app, ['acao', 'petr4,vale3', 'precos', '-f', 'csv'])
        assert r.exit_code == 0, r.output
        assert m.call_args.args[0] == ['PETR4', 'VALE3']
        assert r.output.splitlines() == [
            'Date,PETR4,VALE3',
            '2024-01-02,0.0,1.0',
            '2024-01-03,1.0,2.0',
        ]

    def test_precos_um(self):
        with mock.patch('finbr._yf.precos', return_value=_yf_frame(['PETR4'])):
            r = self.runner.invoke(app, ['acao', 'PETR4', 'precos', '-f', 'csv'])
        assert r.exit_code == 0, r.output
        assert r.output.splitlines()[0] == 'Date,Open,High,Low,Close,Volume'

    def test_precos_json(self):
        with mock.patch('finbr._yf.precos', return_value=_yf_frame(['PETR4', 'VALE3'])):
            r = self.runner.invoke(app, ['acao', 'PETR4,VALE3', 'precos', '-f', 'json'])
        assert r.exit_code == 0, r.output
        primeiro = json.loads(r.output)[0]
        assert primeiro == {'Date': '2024-01-02T00:00:00', 'PETR4': 0.0, 'VALE3': 1.0}

    def test_varios_sem_verbo_compara(self):
        r = self.runner.invoke(app, ['acao', '-f', 'csv', 'AAAA3,CCCC3'])
        assert r.exit_code == 0, r.output
        assert r.output.splitlines()[0] == 'campo,AAAA3,CCCC3'

    def test_verbo_de_um_ticker_rejeita_varios(self):
        r = self.runner.invoke(app, ['acao', 'AAAA3,CCCC3', 'dividendos'])
        assert r.exit_code == 2
        assert 'um ticker' in r.output

    def test_um_ticker_sem_verbo_continua_resumo(self):
        with mock.patch('finbr.statusinvest.acao.detalhes', return_value={'nome': 'X'}) as m:
            r = self.runner.invoke(app, ['acao', '-f', 'csv', 'aaaa3'])
        assert r.exit_code == 0, r.output
        m.assert_called_once_with('AAAA3')

    def test_comparar(self):
        r = self.runner.invoke(app, ['comparar', 'aaaa3', 'bbbb3', '-c', 'p_l,dy', '-f', 'json'])
        assert r.exit_code == 0, r.output
        registros = json.loads(r.output)
        assert registros[0] == {'campo': 'p_l', 'AAAA3': 5.0, 'BBBB3': 15.0}

    def test_comparar_ticker_invalido(self):
        r = self.runner.invoke(app, ['comparar', 'AAAA3', 'ZZZZ3'])
        assert r.exit_code == 2
        assert 'ZZZZ3' in r.output

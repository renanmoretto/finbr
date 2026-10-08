import datetime
import unittest
from unittest import mock

import pandas as pd
from typer.testing import CliRunner

from finbr import correcao
from finbr.cli import app
from finbr.cli._dates import parse_date

# IPCA mensal de dez/2019 a jan/2021 (%); 2020 fecha em 4,52%
IPCA = [1.15, 0.21, 0.25, 0.07, -0.31, -0.38, 0.26, 0.36, 0.24, 0.64, 0.86, 0.89, 1.35, 0.25]
MESES = pd.date_range('2019-12-01', periods=len(IPCA), freq='MS')
DIAS = pd.to_datetime(['2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05', '2024-01-08'])


def _sgs_get(codigo, data_inicio=None, data_fim=None):
    if codigo == 433:
        return pd.DataFrame({433: IPCA}, index=MESES)
    if codigo == 12:
        return pd.DataFrame({12: [1.0] * len(DIAS)}, index=DIAS)
    return pd.DataFrame({codigo: []}, index=pd.DatetimeIndex([]))


class CorrecaoTestCase(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch('finbr.correcao.sgs.get', side_effect=_sgs_get)
        self.sgs_get = patcher.start()
        self.addCleanup(patcher.stop)


class TestMensal(CorrecaoTestCase):
    def test_ano_fechado_bate_com_ipca_oficial(self):
        assert round(correcao.acumulado('ipca', '2020-01-01', '2020-12-01'), 4) == 0.0452

    def test_meses_de_inicio_e_fim_sao_inclusivos(self):
        taxas = correcao.taxas('IPCA', '2020-03-15', '2020-04-20')
        assert [d.strftime('%Y-%m') for d in taxas.index] == ['2020-03', '2020-04']
        assert taxas.round(6).tolist() == [0.0007, -0.0031]

    def test_um_mes(self):
        assert round(correcao.acumulado('ipca', '2020-12-01', '2020-12-31'), 6) == 0.0135

    def test_sem_inicio_usa_12_meses_ate_o_fim(self):
        taxas = correcao.taxas('ipca', fim=datetime.date(2020, 12, 31))
        assert len(taxas) == 12
        assert taxas.index[0].strftime('%Y-%m') == '2020-01'
        assert taxas.index[-1].strftime('%Y-%m') == '2020-12'

    def test_sem_inicio_com_mes_corrente_nao_publicado(self):
        taxas = correcao.taxas('ipca', fim=datetime.date(2021, 2, 10))
        assert len(taxas) == 12
        assert taxas.index[-1].strftime('%Y-%m') == '2021-01'
        assert taxas.index[0].strftime('%Y-%m') == '2020-02'

    def test_sem_inicio_com_mes_anterior_nao_publicado(self):
        taxas = correcao.taxas('ipca', fim=datetime.date(2021, 3, 5))
        assert len(taxas) == 12
        assert taxas.index[0].strftime('%Y-%m') == '2020-02'
        assert taxas.index[-1].strftime('%Y-%m') == '2021-01'

    def test_consulta_o_sgs_pelo_primeiro_dia_dos_meses(self):
        correcao.taxas('ipca', '2020-03-15', '2020-04-20')
        self.sgs_get.assert_called_once_with(
            433, datetime.date(2020, 3, 1), datetime.date(2020, 4, 1)
        )


class TestDiario(CorrecaoTestCase):
    def test_inicio_inclusivo_fim_exclusivo(self):
        taxas = correcao.taxas('cdi', '2024-01-03', '2024-01-08')
        assert [d.day for d in taxas.index] == [3, 4, 5]
        assert round(correcao.acumulado('cdi', '2024-01-03', '2024-01-08'), 6) == 0.030301

    def test_sem_inicio_volta_um_ano(self):
        correcao.taxas('cdi', fim=datetime.date(2024, 1, 9))
        self.sgs_get.assert_called_once_with(
            12, datetime.date(2023, 1, 9), datetime.date(2024, 1, 8)
        )

    def test_sem_inicio_em_29_de_fevereiro(self):
        with self.assertRaises(ValueError):
            correcao.taxas('cdi', fim=datetime.date(2028, 2, 29))
        assert self.sgs_get.call_args.args[1] == datetime.date(2027, 2, 28)

    def test_mesmo_dia_e_periodo_vazio(self):
        with self.assertRaises(ValueError):
            correcao.taxas('cdi', '2024-01-03', '2024-01-03')


class TestCorrigir(CorrecaoTestCase):
    def test_resultado(self):
        r = correcao.corrigir(1000, 'ipca', '2020-01-01', '2020-12-01')
        assert r == {
            'indice': 'ipca',
            'de': datetime.date(2020, 1, 1),
            'ate': datetime.date(2020, 12, 1),
            'periodos': 12,
            'fator': 1.04517342,
            'variacao': 0.045173,
            'valor_inicial': 1000,
            'valor_corrigido': 1045.17,
        }

    def test_periodo_usado_reflete_o_que_foi_publicado(self):
        r = correcao.corrigir(100, 'ipca', '2020-11-01', '2021-06-01')
        assert r['ate'] == datetime.date(2021, 1, 1)
        assert r['periodos'] == 3

    def test_erros(self):
        for args in (
            ('xyz', '2020-01-01', '2020-12-01'),
            ('ipca', '2020-12-01', '2020-01-01'),
            ('ipca', '2030-01-01', '2030-12-01'),
            ('igpm', '2020-01-01', '2020-12-01'),
        ):
            with self.assertRaises(ValueError):
                correcao.corrigir(100, *args)


class TestParseMes(unittest.TestCase):
    def test_ano_mes(self):
        assert parse_date('2020-03') == datetime.date(2020, 3, 1)
        assert parse_date('2020-03-15') == datetime.date(2020, 3, 15)


class TestCli(CorrecaoTestCase):
    def test_acumulado(self):
        r = CliRunner().invoke(
            app, ['macro', 'acumulado', 'ipca', '--de', '2020-01', '--ate', '2020-12', '-f', 'csv']
        )
        assert r.exit_code == 0, r.output
        assert r.output.splitlines() == [
            'campo,valor',
            'indice,ipca',
            'de,2020-01-01',
            'ate,2020-12-01',
            'periodos,12',
            'variacao,0.045173',
        ]

    def test_corrigir(self):
        r = CliRunner().invoke(
            app, ['macro', 'corrigir', '1000', '--de', '2020-01', '--ate', '2020-12', '-f', 'json']
        )
        assert r.exit_code == 0, r.output
        assert '"valor_corrigido": 1045.17' in r.output
        assert '"de": "2020-01-01"' in r.output

    def test_indice_invalido(self):
        r = CliRunner().invoke(app, ['macro', 'acumulado', 'xyz'])
        assert r.exit_code == 2
        assert 'xyz' in r.output

    def test_corrigir_exige_de(self):
        r = CliRunner().invoke(app, ['macro', 'corrigir', '1000'])
        assert r.exit_code == 2

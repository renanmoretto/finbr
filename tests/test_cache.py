import datetime
import io
import os
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from typer.testing import CliRunner

from finbr import _cache, sgs
from finbr.b3 import cotahist
from finbr.cli import app


class CacheTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name) / 'finbr'
        env = mock.patch.dict(os.environ, {'FINBR_CACHE_DIR': str(self.dir)})
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop('FINBR_NO_CACHE', None)

    def _envelhece(self, chave: str, segundos: float) -> None:
        antigo = time.time() - segundos
        os.utime(self.dir / chave, (antigo, antigo))


class TestCache(CacheTestCase):
    def test_miss_grava_e_hit_nao_busca_de_novo(self):
        buscar = mock.Mock(return_value=b'abc')
        assert _cache.obter('ns/x.bin', 60, buscar) == b'abc'
        assert _cache.obter('ns/x.bin', 60, buscar) == b'abc'
        buscar.assert_called_once()
        assert (self.dir / 'ns' / 'x.bin').read_bytes() == b'abc'

    def test_ttl_expira(self):
        _cache.obter('x', 60, lambda: b'velho')
        self._envelhece('x', 61)
        assert _cache.obter('x', 60, lambda: b'novo') == b'novo'
        assert _cache.obter('x', 60, lambda: b'outro') == b'novo'

    def test_ttl_none_nunca_expira(self):
        _cache.obter('x', None, lambda: b'velho')
        self._envelhece('x', 10 * 365 * 24 * 3600)
        assert _cache.obter('x', None, lambda: b'novo') == b'velho'

    def test_erro_na_busca_nao_grava(self):
        def falha():
            raise RuntimeError('fora do ar')

        with self.assertRaises(RuntimeError):
            _cache.obter('x', 60, falha)
        assert not (self.dir / 'x').exists()
        assert _cache.obter('x', 60, lambda: b'ok') == b'ok'

    def test_no_cache_nao_le_nem_grava(self):
        _cache.obter('x', 60, lambda: b'gravado')
        with mock.patch.dict(os.environ, {'FINBR_NO_CACHE': '1'}):
            assert _cache.obter('x', 60, lambda: b'fresco') == b'fresco'
            assert _cache.obter('y', 60, lambda: b'fresco') == b'fresco'
        assert not (self.dir / 'y').exists()
        assert _cache.obter('x', 60, lambda: b'fresco') == b'gravado'

    def test_nao_deixa_arquivo_temporario(self):
        _cache.obter('ns/x', 60, lambda: b'abc')
        assert [p.name for p in (self.dir / 'ns').iterdir()] == ['x']

    def test_diretorio_sem_permissao_ainda_retorna_dados(self):
        with mock.patch.object(Path, 'mkdir', side_effect=PermissionError('negado')):
            with self.assertLogs('finbr._cache', level='WARNING'):
                assert _cache.obter('x', 60, lambda: b'abc') == b'abc'

    def test_info_e_limpar(self):
        assert _cache.info()['arquivos'] == 0
        assert _cache.limpar() == 0
        _cache.obter('a/x', 60, lambda: b'1' * 1000)
        _cache.obter('b/y', 60, lambda: b'2' * 1000)
        info = _cache.info()
        assert info['arquivos'] == 2 and info['diretorio'] == str(self.dir)
        assert _cache.limpar() == 2
        assert _cache.info()['arquivos'] == 0

    def test_diretorio_padrao(self):
        with mock.patch.dict(os.environ, {'XDG_CACHE_HOME': '/tmp/xdg'}):
            os.environ.pop('FINBR_CACHE_DIR')
            assert _cache.diretorio() == Path('/tmp/xdg/finbr')
            os.environ.pop('XDG_CACHE_HOME')
            assert _cache.diretorio() == Path.home() / '.cache' / 'finbr'


def _zip(conteudo: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('COTAHIST.TXT', conteudo)
    return buffer.getvalue()


class TestCotahistCache(CacheTestCase):
    def test_dia_baixa_uma_vez(self):
        resposta = mock.Mock(content=_zip(b'linhas'))
        with mock.patch('finbr.b3.cotahist.requests.get', return_value=resposta) as get:
            data = datetime.date(2024, 10, 15)
            assert cotahist._requests_get_txt(data) == b'linhas'
            assert cotahist._requests_get_txt(data) == b'linhas'
        get.assert_called_once()
        assert (self.dir / 'cotahist' / 'COTAHIST_D15102024.ZIP').is_file()

    def test_ano_baixa_uma_vez(self):
        resposta = mock.Mock(content=_zip(b'linhas'))
        with mock.patch('finbr.b3.cotahist.requests.get', return_value=resposta) as get:
            assert cotahist._requests_get_txt_anual(2020) == b'linhas'
            assert cotahist._requests_get_txt_anual(2020) == b'linhas'
            cotahist._requests_get_txt_anual(2021)
        assert get.call_count == 2

    def test_erro_http_nao_e_cacheado(self):
        resposta = mock.Mock()
        resposta.raise_for_status.side_effect = RuntimeError('404')
        with mock.patch('finbr.b3.cotahist.requests.get', return_value=resposta):
            with self.assertRaises(RuntimeError):
                cotahist._requests_get_txt(datetime.date(2024, 10, 15))
        assert _cache.info()['arquivos'] == 0

    def test_ttl(self):
        hoje = datetime.date.today()
        assert cotahist._ttl_dia(hoje - datetime.timedelta(days=1)) is None
        assert cotahist._ttl_dia(hoje) == _cache.HORA
        assert cotahist._ttl_ano(hoje.year - 1) is None
        assert cotahist._ttl_ano(hoje.year) == 6 * _cache.HORA


class TestSgsCache(CacheTestCase):
    def _resposta(self, valor: str):
        r = mock.Mock(status_code=200)
        r.json.return_value = [{'data': '02/01/2024', 'valor': valor}]
        return r

    def test_mesma_consulta_usa_cache(self):
        with mock.patch('finbr.sgs.requests.get', return_value=self._resposta('0.05')) as get:
            a = sgs.get(12, data_inicio='2024-01-01')
            b = sgs.get(12, data_inicio='2024-01-01')
        get.assert_called_once()
        assert a.equals(b)
        assert a[12].iloc[0] == 0.05

    def test_consultas_diferentes_nao_colidem(self):
        with mock.patch('finbr.sgs.requests.get', return_value=self._resposta('1')) as get:
            sgs.get(12, data_inicio='2024-01-01')
            sgs.get(12, data_inicio='2024-01-02')
            sgs.get(12, data_inicio='2024-01-01', data_fim='2024-02-01')
            sgs.get(433, data_inicio='2024-01-01')
            sgs.get(12)
        assert get.call_count == 5

    def test_expira_em_uma_hora(self):
        with mock.patch('finbr.sgs.requests.get', return_value=self._resposta('1')):
            sgs.get(12)
        self._envelhece('sgs/12_inicio_fim.json', _cache.HORA + 1)
        with mock.patch('finbr.sgs.requests.get', return_value=self._resposta('2')) as get:
            assert sgs.get(12)[12].iloc[0] == 2
        get.assert_called_once()

    def test_erro_nao_e_cacheado(self):
        with mock.patch(
            'finbr.sgs.requests.get', return_value=mock.Mock(status_code=500, text='x')
        ):
            with self.assertRaises(Exception):
                sgs.get(12)
        assert _cache.info()['arquivos'] == 0


class TestCacheCli(CacheTestCase):
    def test_info_e_limpar(self):
        _cache.obter('a/x', 60, lambda: b'1')
        runner = CliRunner()
        r = runner.invoke(app, ['cache', 'info', '-f', 'json'])
        assert r.exit_code == 0, r.output
        assert '"arquivos": 1' in r.output
        r = runner.invoke(app, ['cache', 'limpar'])
        assert r.exit_code == 0, r.output
        assert r.output.startswith('1 arquivo(s)')
        assert _cache.info()['arquivos'] == 0

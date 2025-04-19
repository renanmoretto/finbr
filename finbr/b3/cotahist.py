import io
import zipfile
import datetime
from pathlib import Path

import requests
import pandas as pd
import polars as pl


# metadata
# https://github.com/codigoquant/b3fileparser/blob/main/b3fileparser/b3_meta_data.py
# thanks to codigoquant https://github.com/codigoquant
FIELD_SIZES = {
    'TIPO_DE_REGISTRO': 2,
    'DATA_DO_PREGAO': 8,
    'CODIGO_BDI': 2,
    'CODIGO_DE_NEGOCIACAO': 12,
    'TIPO_DE_MERCADO': 3,
    'NOME_DA_EMPRESA': 12,
    'ESPECIFICACAO_DO_PAPEL': 10,
    'PRAZO_EM_DIAS_DO_MERCADO_A_TERMO': 3,
    'MOEDA_DE_REFERENCIA': 4,
    'PRECO_DE_ABERTURA': 13,
    'PRECO_MAXIMO': 13,
    'PRECO_MINIMO': 13,
    'PRECO_MEDIO': 13,
    'PRECO_ULTIMO_NEGOCIO': 13,
    'PRECO_MELHOR_OFERTA_DE_COMPRA': 13,
    'PRECO_MELHOR_OFERTA_DE_VENDAS': 13,
    'NUMERO_DE_NEGOCIOS': 5,
    'QUANTIDADE_NEGOCIADA': 18,
    'VOLUME_TOTAL_NEGOCIADO': 18,
    'PRECO_DE_EXERCICIO': 13,
    'INDICADOR_DE_CORRECAO_DE_PRECOS': 1,
    'DATA_DE_VENCIMENTO': 8,
    'FATOR_DE_COTACAO': 7,
    'PRECO_DE_EXERCICIO_EM_PONTOS': 13,
    'CODIGO_ISIN': 12,
    'NUMERO_DE_DISTRIBUICAO': 3,
}

DATE_COLUMNS = (
    'DATA_DO_PREGAO',
    'DATA_DE_VENCIMENTO',
)

FLOAT32_COLUMNS = (
    'PRECO_DE_ABERTURA',
    'PRECO_MAXIMO',
    'PRECO_MINIMO',
    'PRECO_MEDIO',
    'PRECO_ULTIMO_NEGOCIO',
    'PRECO_MELHOR_OFERTA_DE_COMPRA',
    'PRECO_MELHOR_OFERTA_DE_VENDAS',
    'PRECO_DE_EXERCICIO',
    'PRECO_DE_EXERCICIO_EM_PONTOS',
)

FLOAT64_COLUMNS = (
    'VOLUME_TOTAL_NEGOCIADO',
    'QUANTIDADE_NEGOCIADA',
)

UINT32_COLUMNS = (
    'FATOR_DE_COTACAO',
    'PRAZO_EM_DIAS_DO_MERCADO_A_TERMO',
    'NUMERO_DE_NEGOCIOS',
    'NUMERO_DE_DISTRIBUICAO',
    'TIPO_DE_REGISTRO',
)

STRING_COLUMNS = (
    'CODIGO_DE_NEGOCIACAO',
    'NOME_DA_EMPRESA',
    'CODIGO_ISIN',
)

CATEGORY_COLUMNS = (
    'INDICADOR_DE_CORRECAO_DE_PRECOS',
    'TIPO_DE_MERCADO',
    'CODIGO_BDI',
    'MOEDA_DE_REFERENCIA',
    'ESPECIFICACAO_DO_PAPEL',
)

MARKETS = {
    '010': 'VISTA',
    '012': 'EXERCICIO_DE_OPCOES_DE_COMPRA',
    '013': 'EXERCÍCIO_DE_OPCOES_DE_VENDA',
    '017': 'LEILAO',
    '020': 'FRACIONARIO',
    '030': 'TERMO',
    '050': 'FUTURO_COM_RETENCAO_DE_GANHO',
    '060': 'FUTURO_COM_MOVIMENTACAO_CONTINUA',
    '070': 'OPCOES_DE_COMPRA',
    '080': 'OPCOES_DE_VENDA',
}

INDOPC = {
    '0': '0',
    '1': 'US$',
    '2': 'TJLP',
    '8': 'IGPM',
    '9': 'URV',
}

CODBDI = {
    '00': '0',
    '02': 'LOTE_PADRAO',
    '05': 'SANCIONADAS PELOS REGULAMENTOS BMFBOVESPA',
    '06': 'CONCORDATARIAS',
    '07': 'RECUPERACAO_EXTRAJUDICIAL',
    '08': 'RECUPERAÇÃO_JUDICIAL',
    '09': 'REGIME_DE_ADMINISTRACAO_ESPECIAL_TEMPORARIA',
    '10': 'DIREITOS_E_RECIBOS',
    '11': 'INTERVENCAO',
    '12': 'FUNDOS_IMOBILIARIOS',
    '13': '13',
    '14': 'CERT.INVEST/TIT.DIV.PUBLICA',
    '18': 'OBRIGACÕES',
    '22': 'BÔNUS(PRIVADOS)',
    '26': 'APOLICES/BÔNUS/TITULOS PUBLICOS',
    '32': 'EXERCICIO_DE_OPCOES_DE_COMPRA_DE_INDICES',
    '33': 'EXERCICIO_DE_OPCOES_DE_VENDA_DE_INDICES',
    '34': '34',
    '35': '35',
    '36': '36',
    '37': '37',
    '38': 'EXERCICIO_DE_OPCOES_DE_COMPRA',
    '42': 'EXERCICIO_DE_OPCOES_DE_VENDA',
    '46': 'LEILAO_DE_NAO_COTADOS',
    '48': 'LEILAO_DE_PRIVATIZACAO',
    '49': 'LEILAO_DO_FUNDO_RECUPERACAO_ECONOMICA_ESPIRITO_SANTO',
    '50': 'LEILAO',
    '51': 'LEILAO_FINOR',
    '52': 'LEILAO_FINAM',
    '53': 'LEILAO_FISET',
    '54': 'LEILAO_DE_ACÕES_EM_MORA',
    '56': 'VENDAS_POR_ALVARA_JUDICIAL',
    '58': 'OUTROS',
    '60': 'PERMUTA_POR_ACÕES',
    '61': 'META',
    '62': 'MERCADO_A_TERMO',
    '66': 'DEBENTURES_COM_DATA_DE_VENCIMENTO_ATE_3_ANOS',
    '68': 'DEBENTURES_COM_DATA_DE_VENCIMENTO_MAIOR_QUE_3_ANOS',
    '70': 'FUTURO_COM_RETENCAO_DE_GANHOS',
    '71': 'MERCADO_DE_FUTURO',
    '74': 'OPCOES_DE_COMPRA_DE_INDICES',
    '75': 'OPCOES_DE_VENDA_DE_INDICES',
    '78': 'OPCOES_DE_COMPRA',
    '82': 'OPCOES_DE_VENDA',
    '83': 'BOVESPAFIX',
    '84': 'SOMA_FIX',
    '90': 'TERMO_VISTA_REGISTRADO',
    '96': 'MERCADO_FRACIONARIO',
    '99': 'TOTAL_GERAL',
}


def _get_txt_from_zip(zip_file: zipfile.ZipFile) -> bytes:
    file_name = zip_file.namelist()[0]
    with zip_file.open(file_name) as f:
        return f.read()


def _requests_get_txt(data: datetime.date, ssl_error: bool = False) -> bytes:
    url = (
        f'https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_D{data.strftime("%d%m%Y")}.ZIP'
    )
    r = requests.get(url, verify=ssl_error)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as thezip:
        return _get_txt_from_zip(thezip)


def _requests_get_txt_anual(ano: int, ssl_error: bool = False) -> bytes:
    url = f'https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ano}.ZIP'
    r = requests.get(url, verify=ssl_error)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as thezip:
        return _get_txt_from_zip(thezip)


def _read_bytes(dados: bytes | io.BytesIO) -> pl.DataFrame:
    df_raw = pl.read_csv(
        dados,
        has_header=False,
        new_columns=['full_str'],
        encoding='latin1',
        truncate_ragged_lines=True,
    )

    slices = {}
    start = 0
    for col_name, width in FIELD_SIZES.items():
        slices[col_name] = (start, width)
        start += width

    df = (
        df_raw.with_columns(
            [
                pl.col('full_str')
                .str.slice(slice_tuple[0], slice_tuple[1])
                .str.strip_chars()
                .alias(col)
                for col, slice_tuple in slices.items()
            ]
        )
        .drop(['full_str'])
        .slice(1, -1)  # dropa cabeçalho erodapé
        .with_columns(
            pl.col(DATE_COLUMNS).replace('', None).str.to_date(format='%Y%m%d'),
            pl.col(FLOAT32_COLUMNS).replace('', None).cast(pl.Float64).truediv(100).round(4),
            pl.col(FLOAT64_COLUMNS).replace('', None).cast(pl.Float64),
            pl.col(UINT32_COLUMNS).replace('', None).cast(pl.UInt32, strict=False),
            pl.col('CODIGO_BDI').map_elements(lambda x: CODBDI.get(x, x), return_dtype=pl.Utf8),
            pl.col('TIPO_DE_MERCADO').map_elements(
                lambda x: MARKETS.get(x, x), return_dtype=pl.Utf8
            ),
            pl.col('INDICADOR_DE_CORRECAO_DE_PRECOS').map_elements(
                lambda x: INDOPC.get(x, x), return_dtype=pl.Utf8
            ),
        )
    )

    return df


def get_ano(ano: int, ssl_error: bool = False) -> pd.DataFrame:
    """Obtém o arquivo COTAHIST da B3 para o ano inteiro especificado.
    Para dados anteriores a 2014, a B3 não possui mais arquivos diários, apenas anuais.

    Parâmetros
    ----------
    ano : int
        Ano para o qual os dados devem ser obtidos.
    ssl_error : bool, default=False
        Se True, levanta erros SSL durante o download.

    Retorna
    -------
    pandas.DataFrame
        DataFrame contendo o arquivo COTAHIST da B3.
    """
    bytes_data = _requests_get_txt_anual(ano, ssl_error=ssl_error)
    df_polars = _read_bytes(bytes_data)
    return df_polars.to_pandas()


def get(data: datetime.date | str, ssl_error: bool = False) -> pd.DataFrame:
    """Obtém o arquivo COTAHIST da B3 para uma data específica via download.

    Parâmetros
    ----------
    data : datetime.date
        Data para a qual os dados devem ser obtidos.
    ssl_error : bool, default=False
        Se True, levanta erros SSL durante o download.

    Retorna
    -------
    pandas.DataFrame
        DataFrame contendo o arquivo COTAHIST da B3.
    """
    if isinstance(data, str):
        data = datetime.datetime.strptime(data, '%Y-%m-%d').date()
    bytes_data = _requests_get_txt(data, ssl_error=ssl_error)
    df_polars = _read_bytes(bytes_data)
    return df_polars.to_pandas()


def read_bytes(dados: bytes | io.BytesIO) -> pd.DataFrame:
    """Lê o arquivo COTAHIST da B3 a partir de bytes ou BytesIO.

    Parâmetros
    ----------
    dados : bytes ou io.BytesIO
        Dados em formato bytes ou BytesIO contendo o arquivo da B3.

    Retorna
    -------
    pandas.DataFrame
        DataFrame contendo dados históricos da B3.
    """
    df_polars = _read_bytes(dados)
    return df_polars.to_pandas()


def read_zip(path: str | Path) -> pd.DataFrame:
    """Lê o arquivo COTAHIST da B3 a partir de um arquivo ZIP.

    Parâmetros
    ----------
    path : str ou Path
        Caminho para o arquivo ZIP contendo os dados da B3.

    Retorna
    -------
    pandas.DataFrame
        DataFrame contendo dados históricos da B3.
    """
    with zipfile.ZipFile(path) as thezip:
        df_polars = _read_bytes(io.BytesIO(_get_txt_from_zip(thezip)))

    return df_polars.to_pandas()


def read_txt(path: str | Path) -> pd.DataFrame:
    """Lê o arquivo COTAHIST da B3 a partir de um arquivo TXT.

    Parâmetros
    ----------
    path : str ou Path
        Caminho para o arquivo TXT contendo os dados da B3.

    Retorna
    -------
    pandas.DataFrame
        DataFrame contendo dados históricos da B3.
    """
    if isinstance(path, str):
        path = Path(path)

    if not path.suffix.lower() == '.txt':
        raise ValueError('path must be a .txt file')

    with open(path, 'rb') as f:
        df_polars = _read_bytes(io.BytesIO(f.read()))

    return df_polars.to_pandas()

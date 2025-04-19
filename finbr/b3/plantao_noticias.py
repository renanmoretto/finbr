import urllib3
import re
import datetime
from dataclasses import dataclass

import requests


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = 'https://sistemasweb.b3.com.br/PlantaoNoticias/Noticias/'


@dataclass
class NoticiaB3:
    def __init__(self, _dict: dict):
        self.informacoes = _dict
        self.id_agencia = _dict['IdAgencia']
        self.conteudo = _dict['content']
        self.data_hora = _dict['dateTime']
        self.titulo = _dict['headline']
        self.id = _dict['id']

        try:
            self.titulo = ''.join(_dict['headline'].split('-')[1:])
        except IndexError:
            self.titulo = 'na'

        try:
            self.empresa = _dict['headline'].split(' - ')[0]
        except IndexError:
            self.empresa = 'na'

        try:
            ticker = re.findall('\((.*?)\)', _dict['headline'])[0]  # type: ignore
            if '-' in ticker:  # ex. LUPA-NM
                ticker = ticker.split('-')[0]
            self.ticker = str(ticker)
        except IndexError:
            self.ticker = 'na'

        self.ano = int(_dict['dateTime'].split(' ')[0].split('-')[0])
        self.mes = int(_dict['dateTime'].split(' ')[0].split('-')[1])
        self.dia = int(_dict['dateTime'].split(' ')[0].split('-')[2])
        self.data = datetime.date(self.ano, self.mes, self.dia)
        self.url = (
            'https://sistemasweb.b3.com.br/PlantaoNoticias/Noticias'
            '/Detail?'
            f'idNoticia={self.id}&'
            f'agencia={self.id_agencia}&'
            f'dataNoticia={self.data_hora.replace(" ", "%20")}'
        )

    def __repr__(self):
        return f'<NoticiaB3 - {" - ".join([str(self.id), self.titulo, self.data_hora])}>'


def _request(inicio: str, fim: str) -> requests.Response:
    url = URL + (f'ListarTitulosNoticias?agencia=18&palavra=&dataInicial={inicio}&dataFinal={fim}')

    r = requests.get(url, verify=False)
    r.raise_for_status()
    return r


def get(
    inicio: str | datetime.date | None = None,
    fim: str | datetime.date | None = None,
) -> list[NoticiaB3]:
    if isinstance(inicio, datetime.date):
        inicio = inicio.isoformat()
    if isinstance(fim, datetime.date):
        fim = fim.isoformat()

    if inicio is None:
        inicio = datetime.date.today().isoformat()
    if fim is None:
        fim = datetime.date.today().isoformat()

    r = _request(inicio, fim)
    if r.status_code == 200:
        noticias = []
        for noticia in r.json():
            noticias.append(NoticiaB3(noticia['NwsMsg']))
        return noticias
    else:
        return r.json()

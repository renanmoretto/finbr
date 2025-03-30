import urllib3
import re
import datetime
from dataclasses import dataclass

import requests


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = 'https://sistemasweb.b3.com.br/PlantaoNoticias/Noticias/'


@dataclass
class NewB3:
    def __init__(self, _dict: dict):
        self.raw_dict = _dict
        self.id_agencia = _dict['IdAgencia']
        self.content = _dict['content']
        self.date_time = _dict['dateTime']
        self.headline = _dict['headline']
        self.id = _dict['id']

        try:
            self.title = ''.join(_dict['headline'].split('-')[1:])
        except IndexError:
            self.title = 'na'

        try:
            self.company = _dict['headline'].split(' - ')[0]
        except IndexError:
            self.company = 'na'

        try:
            ticker = re.findall('\((.*?)\)', _dict['headline'])[0]  # type: ignore
            if '-' in ticker:  # ex. LUPA-NM
                ticker = ticker.split('-')[0]
            self.ticker = str(ticker)
        except IndexError:
            self.ticker = 'na'

        self.year = int(_dict['dateTime'].split(' ')[0].split('-')[0])
        self.month = int(_dict['dateTime'].split(' ')[0].split('-')[1])
        self.day = int(_dict['dateTime'].split(' ')[0].split('-')[2])
        self.date = datetime.date(self.year, self.month, self.day)
        self.url = (
            'https://sistemasweb.b3.com.br/PlantaoNoticias/Noticias'
            '/Detail?'
            f'idNoticia={self.id}&'
            f'agencia={self.id_agencia}&'
            f'dataNoticia={self.date_time.replace(" ", "%20")}'
        )

    def __repr__(self):
        return f'<NewB3 - {" - ".join([str(self.id), self.headline, self.date_time])}>'


def _request(start: str, end: str) -> str:
    url = URL + (f'ListarTitulosNoticias?agencia=18&palavra=&dataInicial={start}&dataFinal={end}')

    r = requests.get(url, verify=False)
    r.raise_for_status()
    return r


def get(
    start: str | datetime.date | None = None, end: str | datetime.date | None = None
) -> list[NewB3]:
    if isinstance(start, datetime.date):
        start = start.isoformat()
    if isinstance(end, datetime.date):
        end = end.isoformat()

    if start is None:
        start = datetime.date.today().isoformat()
    if end is None:
        end = datetime.date.today().isoformat()

    response = _request(start, end)
    if response.status_code == 200:
        news = []
        for new in response.json():
            news.append(NewB3(new['NwsMsg']))
        return news
    else:
        return response.json()

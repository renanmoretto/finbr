import requests
import unidecode


URL = 'https://statusinvest.com.br'


def _fmt_col_name(name: str) -> str:
    if name == '#':
        return 'data'
    return unidecode.unidecode(
        name.lower().replace(' ', '_').replace('_-_(r$)', '').replace('_-_(%)', '')
    )


def _fmt_value(value: str) -> float | str:
    if 'Últ. 12M' in value:
        return 'ltm'

    if value == '-':
        return float('nan')

    cleaned_v = value.replace('.', '').replace(',', '.').replace(' ', '')

    if 'K' in value:
        mult = 1_000
    elif 'M' in value:
        mult = 1_000_000
    elif 'B' in value:
        mult = 1_000_000_000
    elif '%' in value:
        mult = 0.01
    else:
        mult = 1
    cleaned_v = cleaned_v.replace('K', '').replace('M', '').replace('B', '').replace('%', '')

    try:
        value_ok = round(float(cleaned_v) * mult, 4)
    except Exception as _:
        return value

    return value_ok


def _request(path: str, params: dict | None = None) -> requests.Response:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = URL + path
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    return r


def _request_and_parse(
    path: str,
    ticker: str,
    type_: int | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> list[dict]:
    params = {'code': ticker, 'futureData': 'false'}

    if type_ is not None:
        params['type'] = type_
    if start_year is not None:
        params['range.min'] = start_year
    if end_year is not None:
        params['range.max'] = end_year

    r = _request(path, params)
    r_json = r.json()
    grid_data = r_json['data']['grid']

    raw_data = {}
    for grid_data_items in grid_data[:]:
        col_name = grid_data_items['columns'][0]['value']
        for item in grid_data_items['columns'][1:]:
            if item.get('name') in ['AH', 'AV']:
                continue
            col_values = raw_data.get(col_name, [])
            col_values.append(item['value'])
            raw_data[col_name] = col_values

    data = [
        {_fmt_col_name(key): _fmt_value(raw_data[key][i]) for key in raw_data}
        for i in range(len(next(iter(raw_data.values()))))
    ]

    # se annual, str year sem '.0', tipo 2020.0 > '2020'
    if type_ == 0:
        for d in data:
            if 'data' in d.keys():
                d['data'] = str(d['data']).replace('.0', '')

    return data

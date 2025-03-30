# finbr

Collection of Python utilities for Brazilian financial markets.

`finbr` is a comprehensive toolkit designed to simplify working with Brazilian financial markets data. It provides easy access to key financial indicators, market prices, and other essential data for analysis and calculations.

## Installation

```bash
pip install finbr
```

## Features

- Access to Brazilian Central Bank's data (SGS)
- Financial market indicators (CDI, SELIC, IPCA)
- Financial assets price data

## Usage Examples

```python
import finbr

# Asset Prices
prices_data = finbr.prices(['PETR4', 'VALE3'], period='1y')

# CDI (Brazilian Interbank Rate)
# Returns the recent CDI annualized rate, e.g. 0.1415 (14.15%)
annual_cdi = finbr.cdi()
daily_cdi = finbr.cdi(annualized=False)  # daily rate

# SELIC Rate (Brazilian Base Interest Rate)
# Returns the recent SELIC annualized rate e.g. 0.1425 (14.25%)
annual_selic = finbr.selic()  
daily_selic = finbr.selic(annualized=False)  # daily rate

# IPCA (Brazilian Consumer Price Index)
ipca_rate = finbr.ipca()
print(ipca_rate)
# output is a pd.DataFrame
            ipca
date              
1980-02-01  0.0462
1980-03-01  0.0604
1980-04-01  0.0529
1980-05-01  0.0570
1980-06-01  0.0531
...            ...
2024-10-01  0.0056
2024-11-01  0.0039
2024-12-01  0.0052
2025-01-01  0.0016
2025-02-01  0.0131
```

### `finbr.sgs` (SGS - Brazilian Central Bank Time Series)

The `sgs` module provides access to the Brazilian Central Bank's Time Series Management System (SGS). You can find more here: https://www3.bcb.gov.br/sgspub/localizarseries/localizarSeries.do?method=prepararTelaLocalizarSeries

```python
from finbr import sgs

# Get time series by code. Returns a pandas DataFrame.
cdi_series = sgs.get(12)  # CDI
ipca_series = sgs.get(433)  # IPCA

# Get multiple series at once
indicators = sgs.get([12, 433, 189])  # CDI, IPCA, Selic

# Get series with custom names
named_series = sgs.get({12: 'cdi', 433: 'ipca', 189: 'selic'})

# Limit by date range
cdi_2020 = sgs.get(12, start='2020-01-01', end='2020-12-31')

# Search for series
results = sgs.search("IPCA")

# Get metadata for a specific series
metadata = sgs.metadata(433)  # IPCA metadata
```

### `finbr.dias_uteis`

The `dias_uteis` module helps with Brazilian business day calculations, accounting for national holidays.

```python
from datetime import date
import finbr.dias_uteis as du

# Check if a date is a business day
is_workday = du.is_du(date(2023, 5, 1))  # False (Labor Day)

# Get next business day
next_workday = du.next_du()  # Next business day from today

# Get previous business day
prev_workday = du.last_du()  # Previous business day from today

# Add business days to a date
future_date = du.delta_du(date(2023, 1, 2), 5)  # 5 business days after Jan 2

# Get business days between two dates
workdays = du.range_du(date(2023, 1, 1), date(2023, 1, 31))

# Get all business days in a year
year_workdays = du.year_dus(2023)

# Get all holidays in a year
holidays = du.year_holidays(2023)

# Calculate business days between two dates
diff_days = du.diff(date(2023, 1, 1), date(2023, 1, 31))
```

### `finbr.b3`

The `finbr.b3.di1` module provides tools for working with B3's DI1 (Interbank Deposit) futures contracts.

```python
from finbr.b3 import di1

# Verify if a ticker is valid
di1.verify_ticker('DI1F24')  # Valid ticker, no exception raised

# Get the maturity date of a contract
mat_date = di1.maturity_date('DI1F24')  # Returns first business day of Jan 2024

# Calculate days to maturity
days = di1.days_to_maturity('DI1F24')  # Business days until maturity
cal_days = di1.days_to_maturity('DI1F24', business_days=False)  # Calendar days

# Calculate contract price based on interest rate
price = di1.price('DI1F24', 0.10)  # Price at 10% interest rate

# Calculate implied interest rate from price
rate = di1.rate('DI1F24', 95000)  # Interest rate for given price

# Calculate DV01 (dollar value of 1 basis point)
dv01_value = di1.dv01('DI1F24', 0.10)  # Sensitivity to 1bp change in rate
```

The `finbr.b3.cotahist` module processes B3's COTAHIST historical data files containing trading information.

```python
from finbr.b3 import cotahist

# Download data for a specific date
daily_data = cotahist.get('2023-05-15')

# Download data for an entire year
yearly_data = cotahist.get_year(2022)

# From a ZIP file
zip_data = cotahist.read_zip('path/to/COTAHIST_D20230515.ZIP')

# From a TXT file
txt_data = cotahist.read_txt('path/to/COTAHIST_D20230515.TXT')

# From bytes or BytesIO
with open('path/to/file.txt', 'rb') as f:
    bytes_data = cotahist.read_bytes(f.read())
```

The `finbr.b3.plantao_noticias` module fetches corporate news from B3's news feed.

```python
from datetime import date
from finbr.b3 import plantao_noticias

# Get today's news
today_news = plantao_noticias.get()

# Get news for a specific date
spec ific_date_news = plantao_noticias.get('2023-05-15')

# Get news for a date range
date_range_news = plantao_noticias.get('2023-05-01', '2023-05-15')

# Using date objects
start_date = date(2023, 5, 1)
end_date = date(2023, 5, 15)
date_obj_news = plantao_noticias.get(start_date, end_date)

# Working with news objects
for news in today_news:
    print(f"Company: {news.company}")
    print(f"Ticker: {news.ticker}")
    print(f"Title: {news.title}")
    print(f"Date: {news.date}")
    print(f"URL: {news.url}")
    print()
```

### `finbr.statusinvest` *(in development)*

The `statusinvest.acao` module allows you to retrieve stock information from the StatusInvest website (https://statusinvest.com.br/). 
PS: data output is list of dicts

```python
from finbr.statusinvest import acao

# Get basic company information
company_details = acao.details('PETR4')
print(f"Company: {company_details['nome']}")
print(f"CNPJ: {company_details['cnpj']}")
print(f"Market Value: {company_details['valor_de_mercado']}")

# Get income statement data
# By quarter (default)
quarterly_income = acao.income_statement('PETR4')
# By year
annual_income = acao.income_statement('PETR4', period='annual')
# For specific year range
income_range = acao.income_statement('PETR4', start_year=2018, end_year=2022)

# Get balance sheet data
balance = acao.balance_sheet('PETR4')
annual_balance = acao.balance_sheet('PETR4', period='annual')

# Get cash flow data (only annual available)
cash_flow_data = acao.cash_flow('PETR4')

# Get historical multiples
multiples_data = acao.multiples('PETR4')

# Get dividend information
div_history = acao.dividends('PETR4')

# Get payout ratio history
payout_history = acao.payouts('PETR4')

# Get a screener with all stocks
all_stocks = acao.screener()
```

TODOs: FIIs, Stocks, Funds

### `finbr.fundamentus` *(in development)*

The `fundamentus` module allows you to retrieve stock information from the Fundamentus website (https://fundamentus.com.br/).

```python
from finbr import fundamentus

# Get detailed company information and indicators
company_details = fundamentus.details('PETR4')
print(f"P/L: {company_details['p_l']}")
print(f"ROE: {company_details['roe']}")
print(f"Market Value: {company_details['valor_de_mercado']}")

# Get dividend history
dividends = fundamentus.dividends('PETR4')
for div in dividends:
    print(f"Date: {div['data']}, Value: {div['valor']}, Type: {div['tipo']}")

# Get quarterly financial reports information
quarterly = fundamentus.quarterly_results('PETR4')
for q in quarterly:
    print(f"Date: {q['data']}, CVM Link: {q['link_cvm']}")

# Get company presentations
presentations = fundamentus.presentations('PETR4')
for p in presentations:
    print(f"Date: {p['data']}")
    print(f"Description: {p['descricao']}")
    print(f"Download: {p['download_link']}")
```

## License

MIT
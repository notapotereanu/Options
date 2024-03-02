import yfinance as yf
from datetime import date
import datetime
import datetime

symbol = 'SPY'
start_date = '2017-10-01'
end_date = date.today().strftime('%Y-%m-%d')

lower_std = 6.2
upper_std = 1.9
expirationPut = 11

def calculate_bollinger_bands(symbol, start_date, end_date, lower_std, upper_std):
    data = yf.download(symbol, start=start_date, end=end_date)
    data['Rolling Mean'] = data['Close'].rolling(window=20).mean()
    data['Rolling Std'] = data['Close'].rolling(window=20).std()
    data['Upper Band'] = data['Rolling Mean'] + (data['Rolling Std'] * upper_std)
    data['Lower Band'] = data['Rolling Mean'] - (data['Rolling Std'] * lower_std)

    return data

result = calculate_bollinger_bands(symbol, start_date, end_date, lower_std, upper_std)
last_row = result.tail(1)
lower_band_value = last_row['Lower Band'].values[0]

expiration_date = datetime.date.today() + datetime.timedelta(days=expirationPut)
expiration_date_str = expiration_date.strftime('%Y-%m-%d')

ticker = yf.Ticker(symbol)
option_dates = ticker.options
nearest_expiration_date = min(option_dates, key=lambda x: abs(datetime.datetime.strptime(x, '%Y-%m-%d').date() - expiration_date))

option_chain = yf.Ticker(symbol).option_chain(nearest_expiration_date).puts
nearest_row = option_chain.iloc[(option_chain['strike'] - lower_band_value).abs().argsort()[:1]]

print("Strike = "+ str(nearest_row.strike.values[0]))
print("Expiration Date = "+ str(nearest_expiration_date))
print("LastPrice = "+ str(nearest_row.lastPrice.values[0]))
print("Bid = "+ str(nearest_row.bid.values[0]))
print("PercentChange = "+ str(nearest_row.percentChange.values[0]))
print("OpenInterest = "+ str(nearest_row.openInterest.values[0]))
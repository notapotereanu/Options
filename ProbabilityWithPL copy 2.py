import glob
import yfinance as yf
import pandas as pd
from datetime import timedelta
import warnings
import time ,os
from Portafolio import Portfolio

warnings.filterwarnings("ignore")

def getStockDataWithBolinger(ticker, start_date, deviationUpper, deviationLower):
    print('Loading stock data for: ' + ticker)
    data = yf.download(ticker, start=start_date)
    data['SMA'] = data['Close'].rolling(window=20).mean()
    data['STD'] = data['Close'].rolling(window=20).std()
    data['Upper'] = data['SMA'] + (data['STD'] * deviationUpper)
    data['Lower'] = data['SMA'] - (data['STD'] * deviationLower)
    return  data    

def loadOptionsDataframe(pattern):
    csv_files = glob.glob(pattern)
    dfs = []
    for csv_file in csv_files:
        print('Loading file: ' + csv_file)
        df = pd.read_csv(csv_file)
        dfs.append(df)
    df = pd.concat(dfs, ignore_index=True)
    df['expiration'] = pd.to_datetime(df['expiration'], format='%m/%d/%Y').dt.strftime('%d/%m/%Y')
    df['quotedate'] = pd.to_datetime(df['quotedate'], format='%m/%d/%Y').dt.strftime('%d/%m/%Y')

    df['expiration'] = pd.to_datetime(df['expiration'], format='%d/%m/%Y')
    df['quotedate'] = pd.to_datetime(df['quotedate'], format='%d/%m/%Y')

    # Sort DataFrame by quotedate and strike
    df.sort_values(by=['quotedate', 'strike'], inplace=True)

    return df
    
def findPutorCallOptionsToOpen(df_options, strikePriceSearched, dateSearched ,expirationDateSearched, typeSearched):
    df = df_options[df_options['quotedate'] == dateSearched]
    df = df[df['type'] == typeSearched]
    df = df[df['expiration'] <= expirationDateSearched]
    if df.empty:
        return 'No options found that match the given criteria.'
    nearest_expiration = df['expiration'].max()
    df = df[df['expiration'] == nearest_expiration]
    closest_index = (df['strike'] - strikePriceSearched).abs().idxmin()
    df = df.loc[closest_index]
    return df

def trackingCurrentDayPL(df_options, df_stock, portafoglio: Portfolio, tracking: list, todaysDate, trackType):
    new_row = {'date': todaysDate, 
           'totalCapital': round(portafoglio.totalCapital,2) , 
           'unrializedPnL': 0, 
           'rializedPnL': 0, 
           'stocksOwned': portafoglio.stocksOwned,
           'stocksPriceToday':round(df_stock.loc[todaysDate, 'Close'],2),
           'stocksPriceBoughtAt': portafoglio.stocksPriceBoughtAt,
           'putOwned': portafoglio.putOwned,
           'putOwnedSoldAt': portafoglio.putOwnedSoldAt,
           'putPriceToday': 0,
           'putOwnedContract': portafoglio.putOwnedContract,
           'putOwnedStrike': portafoglio.putStrikePrice,
           'callOwned': portafoglio.callOwned,
           'callOwnedSoldAt': portafoglio.callOwnedSoldAt,
           'callPriceToday': 0,
           'callOwnedContract': portafoglio.callOwnedContract,
           'callOwnedStrike': portafoglio.callStrikePrice,
           'trackType': trackType
           }

    if trackType == 'expirationDay' or trackType == 'optionNotFound':
        new_row['unrializedPnL'] = portafoglio.unrializedPnL
        new_row['rializedPnL'] = portafoglio.rializedPnL
        new_row['callPriceToday'] = 0
        new_row['putPriceToday'] = 0
    else:
        underliazed = 0
        putPriceToday = 0
        callPriceToday = 0
        
        if portafoglio.stocksOwned > 0:
            originalValue = portafoglio.stocksOwned * portafoglio.stocksPriceBoughtAt
            todaysValue = df_stock.loc[todaysDate, 'Close'] * portafoglio.stocksOwned
            underliazed = underliazed + (todaysValue - originalValue)

        if portafoglio.putOwned > 0:
            originalValue = portafoglio.putOwned * portafoglio.putOwnedSoldAt 
            row = df_options[(df_options['optionroot'] == portafoglio.putOwnedContract) & (df_options['quotedate'] == todaysDate)]
            ask_value = row['ask'].values[0]
            putPriceToday = ask_value
            todaysValue =  ask_value * portafoglio.putOwned
            underliazed = (underliazed + (originalValue - todaysValue) * 100) 

        if portafoglio.callOwned > 0:
            originalValue = portafoglio.callOwned * portafoglio.callOwnedSoldAt
            row = df_options[(df_options['optionroot'] == portafoglio.callOwnedContract) & (df_options['quotedate'] == todaysDate)]
            ask_value = row['ask'].values[0]
            callPriceToday = ask_value
            todaysValue = ask_value * portafoglio.callOwned
            underliazed = (underliazed + (originalValue - todaysValue)* 100) 
        portafoglio.unrializedPnL = round(underliazed,2)

        new_row['unrializedPnL'] = portafoglio.unrializedPnL
        new_row['callPriceToday'] = callPriceToday
        new_row['putPriceToday'] = putPriceToday
    
    tracking.append(new_row)

def closePutOption(leverage, portafoglio, trackingFileName, df_stock, todaysDate, tracking,reason):
    unrializedPnL = 0
    if portafoglio.putStrikePrice > df_stock.loc[todaysDate, 'Close']: # Assigned
        portafoglio.stocksOwned = portafoglio.putOwned * 100 * leverage
        portafoglio.stocksPriceBoughtAt = portafoglio.putStrikePrice
        unrializedPnL = (df_stock.loc[todaysDate, 'Close'] - portafoglio.putStrikePrice) * portafoglio.stocksOwned

    portafoglio.rializedPnL = round(portafoglio.putOwnedSoldAt * 100 * portafoglio.putOwned, 2)
    portafoglio.totalCapital = round(portafoglio.totalCapital + round(portafoglio.rializedPnL, 2), 2)
    portafoglio.unrializedPnL = round(unrializedPnL,2)

    tracking = trackingCurrentDayPL(df_options, df_stock, portafoglio, tracking, todaysDate, reason)

    portafoglio.rializedPnL = 0
    portafoglio.putOwned = 0
    portafoglio.putOwnedContract = ""
    portafoglio.putOwnedSoldAt = 0
    portafoglio.putStrikePrice = 0 
    return tracking

def closeCallOption(leverage, portafoglio, trackingFileName, df_stock, todaysDate, tracking, reason):
    rializedPnLStocks = 0

    if portafoglio.callStrikePrice < df_stock.loc[todaysDate, 'Close']:  # Assigned
        rializedPnLStocks = (portafoglio.callStrikePrice  - portafoglio.stocksPriceBoughtAt) * portafoglio.stocksOwned 
        portafoglio.stocksOwned = 0
        portafoglio.stocksPriceBoughtAt = 0
    else:
        portafoglio.unrializedPnL = round((df_stock.loc[todaysDate, 'Close'] - portafoglio.stocksPriceBoughtAt) * portafoglio.callOwned * leverage * 100,2)

    portafoglio.rializedPnL = round(portafoglio.callOwnedSoldAt * portafoglio.callOwned * leverage * 100 + rializedPnLStocks,2)
    portafoglio.totalCapital = round(portafoglio.totalCapital + round(portafoglio.rializedPnL, 2), 2)

    tracking = trackingCurrentDayPL(df_options, df_stock, portafoglio, tracking, todaysDate, reason)

    portafoglio.rializedPnL = 0
    portafoglio.callOwned = 0
    portafoglio.callOwnedSoldAt = 0
    portafoglio.callOwnedContract = ""
    portafoglio.callStrikePrice = 0
    return tracking

def calculateProfit(df_options, leverage, deviationLower, deviationUpper, expirationDaysPut, expirationDaysCall):
    portafoglio = Portfolio(0)
    trackingFileName = f'tracking_L_{deviationLower}_U_{deviationUpper}_EP_{expirationDaysPut}_EC_{expirationDaysCall}L_{leverage}.csv'
    if os.path.isfile(trackingFileName):
        return
    df_stock = getStockDataWithBolinger('SPY', '2017-10-01', deviationUpper, deviationLower)
    unique_dates = sorted(df_options['quotedate'].unique())
    start_time = time.time()
    tracking = []

    for todaysDate in unique_dates:
        if portafoglio.stocksOwned == 0 and portafoglio.putOwned == 0 and portafoglio.callOwned == 0:
            expirationDate = (todaysDate + timedelta(days=expirationDaysPut)).strftime('%Y-%m-%d')
            lowerBand, higherBand = df_stock.loc[todaysDate, ['Lower', 'Upper']]
            nextPutOption = findPutorCallOptionsToOpen(df_options, lowerBand, todaysDate, expirationDate, 'put')
            if round(nextPutOption['bid'] - 0.02, 2) <= 0:
                trackingCurrentDayPL(df_options, df_stock, portafoglio, tracking, todaysDate, 'bidTooLow')
                continue
            portafoglio.putOwnedSoldAt = round(nextPutOption['bid'] - 0.02, 2) #commissioni
            portafoglio.putOwnedContract = nextPutOption['optionroot']
            portafoglio.putOwned = 1 * leverage
            portafoglio.putStrikePrice = nextPutOption['strike']
        elif portafoglio.stocksOwned > 0 and portafoglio.callOwned == 0:
            expirationDate = (todaysDate + timedelta(days=expirationDaysCall)).strftime('%Y-%m-%d')
            lowerBand, higherBand = df_stock.loc[todaysDate, ['Lower', 'Upper']]
            nextCallOption = findPutorCallOptionsToOpen(df_options, higherBand, todaysDate, expirationDate, 'call')
            if round(nextCallOption['bid'] - 0.02, 2) <= 0:
                trackingCurrentDayPL(df_options, df_stock, portafoglio, tracking, todaysDate, 'bidTooLow')
                continue
            portafoglio.callOwnedSoldAt = round(nextCallOption['bid'] - 0.02, 2)  #commissioni
            portafoglio.callOwnedContract = nextCallOption['optionroot']
            portafoglio.callOwned = 1 * leverage
            portafoglio.callStrikePrice = nextCallOption['strike']

        if portafoglio.putOwned > 0:
            row = df_options[(df_options['optionroot'] == portafoglio.putOwnedContract) & (df_options['quotedate'] == todaysDate)]
            if row.empty:
                closeCallOption(leverage,portafoglio, trackingFileName, df_stock, todaysDate, tracking,'optionNotFound')
                continue
        elif portafoglio.callOwned > 0:
            row = df_options[(df_options['optionroot'] == portafoglio.callOwnedContract) & (df_options['quotedate'] == todaysDate)]
            if row.empty:
                closeCallOption(leverage, portafoglio, trackingFileName, df_stock, todaysDate, tracking,'optionNotFound')
                continue
        else:
            raise Exception('Error: no positions to close')

        if todaysDate == row.expiration.values[0]:
            print('Expiration day '+ todaysDate.strftime('%Y-%m-%d') + ' ' + trackingFileName)
            if portafoglio.putOwned > 0:
                closePutOption(leverage, portafoglio, trackingFileName, df_stock, todaysDate, tracking, 'expirationDay')
                continue
            if portafoglio.callOwned > 0:
                closeCallOption(leverage, portafoglio, trackingFileName, df_stock, todaysDate, tracking, 'expirationDay')
                continue
                        
        trackingCurrentDayPL(df_options, df_stock, portafoglio, tracking, todaysDate, 'normalDay')
    tracking = pd.DataFrame(tracking)
    tracking.to_csv(trackingFileName, index=False)
    end_time = time.time()
    print('Execution time: ' + str(end_time - start_time) + ' seconds')

leverage = 1
deviationLowerArray = [1.1, 1.3,  1.5,  1.7, 1.9, 2.1,  2.3,  2.5,  2.7, 2.9]
deviationUpperArray =  [1.1, 1.3,  1.5,  1.7, 1.9, 2.1,  2.3,  2.5,  2.7, 2.9]
expirationDaysPutArray = [3, 7,  21, 31, 42, 70, 100, 161, 210, 275, 325]
expirationDaysCallArray = [3, 7,  21, 31 , 42, 70, 100, 161, 210, 275, 325]
df_options = loadOptionsDataframe('HistoricalOptionsCSV/SPY_20*.csv')
#df_options = pd.read_csv("df_options_full.csv")

deviationLowerArray = [1.5]

for deviationLower in deviationLowerArray:
    for deviationUpper in deviationUpperArray:
        for expirationDaysPut in expirationDaysPutArray:
            for expirationDaysCall in expirationDaysCallArray:
                calculateProfit(df_options, leverage, deviationLower, deviationUpper, expirationDaysPut, expirationDaysCall)
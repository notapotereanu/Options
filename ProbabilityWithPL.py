import glob
import yfinance as yf
import pandas as pd
from datetime import timedelta
import warnings
import time ,os
import numpy as np
from Portafolio import Portfolio
import argparse
import ast

warnings.filterwarnings("ignore")

def getStockData(ticker, start_date):
    print('Loading stock data for: ' + ticker)
    data = yf.download(ticker, start=start_date)
    return  data    

def getBolingherBands(data, deviationUpper, deviationLower):
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
    dfFilteredByDate = df_options.loc[dateSearched]
    dfFilteredByDateAndOptionType = dfFilteredByDate[dfFilteredByDate['type'] == typeSearched]
    dfFilteredByDTE = dfFilteredByDateAndOptionType[dfFilteredByDateAndOptionType['expiration'] <= expirationDateSearched]
    if dfFilteredByDTE.empty:
        return 'No options found that match the given criteria.'
    nearest_expiration = dfFilteredByDTE['expiration'].max()
    dfFilteredByNearestExpiration = dfFilteredByDTE[dfFilteredByDTE['expiration'] == nearest_expiration]
    min_difference = (dfFilteredByNearestExpiration['strike'] - strikePriceSearched).abs().min()
    return dfFilteredByNearestExpiration[(dfFilteredByNearestExpiration['strike'] - strikePriceSearched).abs() == min_difference]

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
        putPriceToday = 0
        underliazed = 0
        callPriceToday = 0
        
        if portafoglio.stocksOwned > 0:
            originalValue = portafoglio.stocksOwned * portafoglio.stocksPriceBoughtAt
            todaysValue = df_stock.loc[todaysDate, 'Close'] * portafoglio.stocksOwned
            underliazed = underliazed + (todaysValue - originalValue)

        if portafoglio.putOwned > 0:
            originalValue = portafoglio.putOwned * portafoglio.putOwnedSoldAt 
            
            row = df_options.loc[todaysDate]
            row = row[row['optionroot'] == portafoglio.putOwnedContract]
            
            putPriceToday = row['ask'].values[0]
            todaysValue =  putPriceToday * portafoglio.putOwned
            underliazed = (underliazed + (originalValue - todaysValue) * 100) 

        if portafoglio.callOwned > 0:
            originalValue = portafoglio.callOwned * portafoglio.callOwnedSoldAt
            
            row = df_options.loc[todaysDate]
            row = row[row['optionroot'] == portafoglio.callOwnedContract]
            
            callPriceToday = row['ask'].values[0]
            todaysValue = callPriceToday * portafoglio.callOwned
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

def calculateProfit(df_options,df_stock, leverage, expirationDaysPut, expirationDaysCall,trackingFileName):
    portafoglio = Portfolio(0)

    unique_dates = sorted(df_options.index.unique().tolist())
    tracking = []

    for todaysDate in unique_dates:
        if portafoglio.stocksOwned == 0 and portafoglio.putOwned == 0 and portafoglio.callOwned == 0:
            expirationDate = (todaysDate + timedelta(days=expirationDaysPut)).strftime('%Y-%m-%d')
            lowerBand, higherBand = df_stock.loc[todaysDate, ['Lower', 'Upper']]
            nextPutOption = findPutorCallOptionsToOpen(df_options, lowerBand, todaysDate, expirationDate, 'put')
            if round(nextPutOption['bid'].iloc[0] - 0.02, 2) <= 0:
                trackingCurrentDayPL(df_options, df_stock, portafoglio, tracking, todaysDate, 'bidTooLow')
                continue
            portafoglio.putOwnedSoldAt = round(nextPutOption['bid'].iloc[0] - 0.02, 2) #commissioni
            portafoglio.putOwnedContract = nextPutOption['optionroot'].iloc[0]
            portafoglio.putOwned = 1 * leverage
            portafoglio.putStrikePrice = nextPutOption['strike'].iloc[0]
        elif portafoglio.stocksOwned > 0 and portafoglio.callOwned == 0:
            expirationDate = (todaysDate + timedelta(days=expirationDaysCall)).strftime('%Y-%m-%d')
            lowerBand, higherBand = df_stock.loc[todaysDate, ['Lower', 'Upper']]
            nextCallOption = findPutorCallOptionsToOpen(df_options, higherBand, todaysDate, expirationDate, 'call')
            if round(nextCallOption['bid'].iloc[0] - 0.02, 2) <= 0:
                trackingCurrentDayPL(df_options, df_stock, portafoglio, tracking, todaysDate, 'bidTooLow')
                continue
            portafoglio.callOwnedSoldAt = round(nextCallOption['bid'].iloc[0] - 0.02, 2)  #commissioni
            portafoglio.callOwnedContract = nextCallOption['optionroot'].iloc[0]
            portafoglio.callOwned = 1 * leverage
            portafoglio.callStrikePrice = nextCallOption['strike'].iloc[0]

        if portafoglio.putOwned > 0:
            row = df_options.loc[todaysDate]
            row = row[row['optionroot'] == portafoglio.putOwnedContract]
            if row.empty:
                closeCallOption(leverage,portafoglio, trackingFileName, df_stock, todaysDate, tracking,'optionNotFound')
                continue
        elif portafoglio.callOwned > 0:
            row = df_options.loc[todaysDate]
            row = row[row['optionroot'] == portafoglio.callOwnedContract]
            if row.empty:
                closeCallOption(leverage, portafoglio, trackingFileName, df_stock, todaysDate, tracking,'optionNotFound')
                continue
        else:
            raise Exception('Error: no positions to close')

        if todaysDate == row.expiration.values[0]:
            if portafoglio.putOwned > 0:
                closePutOption(leverage, portafoglio, trackingFileName, df_stock, todaysDate, tracking, 'expirationDay')
                continue
            if portafoglio.callOwned > 0:
                closeCallOption(leverage, portafoglio, trackingFileName, df_stock, todaysDate, tracking, 'expirationDay')
                continue
                        
        trackingCurrentDayPL(df_options, df_stock, portafoglio, tracking, todaysDate, 'normalDay')
    tracking = pd.DataFrame(tracking)
    tracking.to_csv(trackingFileName, index=False)
    with open('trackingCSV.txt', 'a', encoding='utf-16') as file:
        file.write(trackingFileName + '\n')

leverage = 1
import math

expirationDaysPut = [1]
for _ in range(10):  # We already have the first value, so we only need 10 more
    next_value = expirationDaysPut[-1] * 1.61
    expirationDaysPut.append(math.ceil(next_value))  # Round up to the nearest integer

expirationDaysPut = [3, 6, 11, 19, 32, 53, 87, 142, 230, 372]
expirationDaysCall = [3, 6, 11, 19, 32, 53, 87, 142, 230, 372]

df_options = loadOptionsDataframe('HistoricalOptionsCSV/SPY_2*.csv')
df_options = df_options.set_index('quotedate', drop=False)
df_options = df_options.sort_index()
df_stock = getStockData('SPY', '2017-10-01')

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--deviationLowerArrayFrom', type=ast.literal_eval, default=[],
                    help='An array to be passed to the script')
parser.add_argument('--deviationLowerArrayTo', type=ast.literal_eval, default=[],
                    help='Another array to be passed to the script')

args = parser.parse_args()
deviationLowerArrayFrom = args.deviationLowerArrayFrom[0]
deviationLowerArrayTo = args.deviationLowerArrayTo[0]

def checkFileExists(filename, target_line):
    with open(filename, 'r', encoding='utf-16') as file:
        for line in file:
            if line.strip() == target_line:
                return True
    return False

for deviationLower in np.arange(deviationLowerArrayFrom, deviationLowerArrayTo, 0.1) :
    for deviationUpper in np.arange(0, 5, 0.1):
        for expirationDaysPutSingle in expirationDaysPut:
            for expirationDaysCallSingle in expirationDaysCall:
                start_time = time.time()
                trackingFileName = f'Tracking/tracking_L_{round(deviationLower,2)}_U_{round(deviationUpper,2)}_EP_{expirationDaysPutSingle}_EC_{expirationDaysCallSingle}L_{leverage}.csv'
                if checkFileExists('trackingCSV.txt', trackingFileName):
                    continue
                df_stock_bolingher = getBolingherBands(df_stock, round(deviationUpper,2), round(deviationLower,2))
                calculateProfit(df_options, df_stock_bolingher, leverage, expirationDaysPutSingle, expirationDaysCallSingle,trackingFileName)
                end_time = time.time()
                print('Execution time: ' + str(end_time - start_time) + ' seconds' + ' L: '
                      + str(round(deviationLower,2)) + ' U: ' + str(round(deviationUpper,2)) + 
                      ' EP: ' + str(expirationDaysPutSingle) + ' EC: ' + str(expirationDaysCallSingle) + 
                      ' L: ' + str(leverage))
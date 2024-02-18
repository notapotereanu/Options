import pandas as pd
import os
import re
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import yfinance as yf

expirationDaysPut = [6, 11, 19, 32, 53, 87, 142, 230, 372]

def analyze_tracking_data():
    folderName = 'Tracking_ARCHIVE'
    csv_files = [f for f in os.listdir(folderName) if f.endswith('.csv')]

    data = []

    for csv_file in csv_files:
        if os.path.getsize(f'{folderName}/{csv_file}') == 0:
            print(f'The file {csv_file} is empty. Skipping...')
            continue

        lower = re.search('L_(.*?)_', csv_file).group(1)
        upper = re.search('U_(.*?)_', csv_file).group(1)
        expiration_put = re.search('EP_(.*?)_', csv_file).group(1)
        expiration_call = re.search('EC_(.*?)_', csv_file).group(1).split("L")[0]

        df = pd.read_csv(f'{folderName}/{csv_file}')

        df['callOwnedCount'] = (df['callOwned'] == 1).cumsum()
        df['putOwnedCount'] = (df['putOwned'] == 1).cumsum()
        df['stockOwnedCount'] = (df['stocksOwned'] == 100).cumsum()

        last_row = df.iloc[-1]
        capital = last_row['totalCapital'] + last_row['unrializedPnL'] + last_row['rializedPnL']

        max_loss_pl_unrealized = df['unrializedPnL'].min()
        max_loss_pl_realized = df['rializedPnL'].min()

        call_owned_strike_count = last_row['callOwnedCount']
        put_owned_strike_count = last_row['putOwnedCount']
        stock_owned_count = last_row['stockOwnedCount']

        data.append([lower, upper, expiration_put, expiration_call, capital, max_loss_pl_unrealized, max_loss_pl_realized, call_owned_strike_count, put_owned_strike_count, stock_owned_count])

    final_df = pd.DataFrame(data, columns=['Lower', 'Upper', 'ExpirationPut', 'ExpirationCall', 'Capital', 'MaxLossPLUnRealized', 'MaxLossPLRealized', 'CallOwnedStrikeCount', 'PutOwnedStrikeCount', 'StockOwnedCount'])

    final_df = final_df.sort_values(by=['Lower', 'Upper', 'ExpirationPut', 'ExpirationCall', 'Capital', 'MaxLossPLUnRealized', 'MaxLossPLRealized', 'CallOwnedStrikeCount', 'PutOwnedStrikeCount', 'StockOwnedCount'])

    final_df.to_csv('TrackingAnalizer.csv', index=False)

def visualize_tracking_data():
    df = pd.read_csv('TrackingAnalizer.csv')
    list_df = []
    for i in expirationDaysPut:
        df_filtered = df[df['ExpirationPut'] == i]
        agg_df = df_filtered.groupby(['Lower', 'Upper'])['Capital'].max().reset_index()
        pivot_df = agg_df.pivot(index='Lower', columns='Upper', values='Capital')
        list_df.append(pivot_df)

    # Create a figure and a grid of subplots
    fig, axs = plt.subplots(3, 3, figsize=(15, 15))

    # Loop over the list of DataFrames and create a heatmap for each one
    for i, df in enumerate(list_df):
        row = i // 3
        col = i % 3
        sns.heatmap(df, cmap='YlGnBu', ax=axs[row, col])
        axs[row, col].set_title(f'Heatmap of Capital by Lower and Upper for ExpirationPut = {expirationDaysPut[i]}')

    # Remove any unused subplots
    for j in range(i+1, 9):
        fig.delaxes(axs.flatten()[j])

    plt.tight_layout()
    plt.show()

def analyze_tracking_particular_lower_upper(lower, upper):
    directory = 'Tracking_ARCHIVE'  # replace with your directory

    # Initialize an empty DataFrame
    data = []
    for filename in os.listdir(directory):
        if filename.startswith(f'tracking_L_{lower}_U_{upper}') and filename.endswith('.csv'):
            file_path = os.path.join(directory, filename)
            print(f'Processing file: {file_path}')

            # Read the CSV file into a DataFrame
            df = pd.read_csv(file_path)

            # Add a new column that counts the cumulative times when callOwnedStrike is not equal to 0.0
            df['callOwnedStrikeCount'] = (df['callOwnedStrike'] != 0.0).cumsum()

            # Get the last row of the DataFrame
            last_row = df.iloc[-1]

            # Perform the operations
            capital = last_row['totalCapital'] + last_row['unrializedPnL'] + last_row['rializedPnL']
            max_loss_pl_unrealized = df['unrializedPnL'].min()
            max_loss_pl_realized = df['rializedPnL'].min()
            call_owned_strike_count = last_row['callOwnedStrikeCount']

            # Extract additional data from the filename
            lower = re.search('L_(.*?)_', filename).group(1)
            upper = re.search('U_(.*?)_', filename).group(1)
            expiration_put = re.search('EP_(.*?)_', filename).group(1)
            expiration_call = re.search('EC_(.*?)_', filename).group(1).split("L")[0]

            # Append the data to the DataFrame
            data.append([lower, upper, expiration_put, expiration_call, capital, max_loss_pl_unrealized, max_loss_pl_realized, call_owned_strike_count])

    final_df =  pd.DataFrame(data, columns=['Lower', 'Upper', 'ExpirationPut', 'ExpirationCall', 'Capital', 'MaxLossPLUnRealized', 'MaxLossPLRealized', 'CallOwnedStrikeCount'])
    return final_df.sort_values(by=['Lower', 'Upper', 'ExpirationPut', 'ExpirationCall', 'Capital', 'MaxLossPLUnRealized', 'MaxLossPLRealized', 'CallOwnedStrikeCount'])

def visualize_tracking_particular_lower_upper(lower,upper):
    df = analyze_tracking_particular_lower_upper(lower,upper)
    
    df['Lower'] = pd.to_numeric(df['Lower'], errors='coerce')
    df['Upper'] = pd.to_numeric(df['Upper'], errors='coerce')
    df['ExpirationPut'] = pd.to_numeric(df['ExpirationPut'], errors='coerce')
    df['ExpirationCall'] = pd.to_numeric(df['ExpirationCall'], errors='coerce')
    
    pivot_df = df.pivot(index='ExpirationPut', columns='ExpirationCall', values='Capital')
    annot_df = df.pivot(index='ExpirationPut', columns='ExpirationCall', values='CallOwnedStrikeCount')
    
    fig, ax = plt.subplots(figsize=(10, 10))
    sns.heatmap(pivot_df, cmap='YlGnBu', ax=ax, annot=annot_df, fmt='d')
    ax.set_title(f'Heatmap of Capital by Expiration Put and Expiration Call {lower} {upper}')
    plt.tight_layout()
    plt.show()

def visualize_strategy_with_spy(lower, upper, expirationPut, expirationCall):
    directory = 'Tracking_ARCHIVE'  # replace with your directory
    if expirationCall == 0:
        expirationCall = ""
    tickerData = yf.Ticker("SPY")
    for filename in os.listdir(directory):
        if filename.startswith(f'tracking_L_{lower}_U_{upper}_EP_{expirationPut}_EC_{expirationCall}') and filename.endswith('.csv'):
            file_path = os.path.join(directory, filename)
            print(f'Processing file: {file_path}')

            df = pd.read_csv(file_path)
            df = df[df['trackType'] != 'expirationDay']
            df['date'] = pd.to_datetime(df['date'])
            df['callOwnedContract'] = pd.to_numeric(df['callOwnedContract'], errors='coerce')

            df['Options Capital'] = df['totalCapital'] + df['unrializedPnL'] + df['rializedPnL']
            tickerDf = tickerData.history(period='1d', start='2018-11-01', end='2023-11-30')
            tickerDf['Stock Capital'] = tickerDf['Close'] * 100 - 25059 # 25059 is the initial capital
            
            plt.figure(figsize=(14, 7))
            plt.plot(tickerDf.index, tickerDf['Stock Capital'], label='Stock Capital')
            plt.plot(df['date'], df['Options Capital'], label='Options Capital')
            
            # Get the limits of the y-axis
            ymin, ymax = plt.ylim()

            # Fill between ymin and ymax where 'callOwnedContract' is 1
            plt.fill_between(df['date'], ymin, ymax, where=df['callOwnedStrike'] != 0.0, color='grey', alpha=0.5)

            # Fill between ymin and ymax where 'trackType' is 'bidTooLow'
            plt.fill_between(df['date'], ymin, ymax, where=df['trackType'] == 'bidTooLow', color='red', alpha=0.5)
            plt.xlabel('Date')
            plt.ylabel('Capital')
            plt.title('Capital Over Time')
            plt.legend()
            plt.grid(True)
            plt.show()


analyze_tracking_data()
#visualize_tracking_data()
#visualize_tracking_particular_lower_upper(5.1,7.7)
#visualize_strategy_with_spy(5.1, 7.7, 6, 3)

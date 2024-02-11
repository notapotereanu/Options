import pandas as pd
import os
import re
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
    
def analyze_tracking_data():
    # List all CSV files in the Tracking folder
    csv_files = [f for f in os.listdir('Tracking_ARCHIVE') if f.endswith('.csv')]

    data = []

    # Process each CSV file
    for csv_file in csv_files:
        # Skip if the file is empty
        if os.path.getsize(f'Tracking_ARCHIVE/{csv_file}') == 0:
            print(f'The file {csv_file} is empty. Skipping...')
            continue

        # Extract values from the file name
        lower = re.search('L_(.*?)_', csv_file).group(1)
        upper = re.search('U_(.*?)_', csv_file).group(1)
        expiration_put = re.search('EP_(.*?)_', csv_file).group(1)
        expiration_call = re.search('EC_(.*?)_', csv_file).group(1).split("L")[0]

        # Read the CSV file into a DataFrame
        df = pd.read_csv(f'Tracking_ARCHIVE/{csv_file}')

        # Calculate the Capital
        last_row = df.iloc[-1]
        capital = last_row['totalCapital'] + last_row['unrializedPnL'] + last_row['rializedPnL']

        # Calculate MaxLossPLUnRealized and MaxLossPLRealized
        max_loss_pl_unrealized = df['unrializedPnL'].min()
        max_loss_pl_realized = df['rializedPnL'].min()

        # Append the data
        data.append([lower, upper, expiration_put, expiration_call, capital, max_loss_pl_unrealized, max_loss_pl_realized])

    # Create the final DataFrame
    final_df = pd.DataFrame(data, columns=['Lower', 'Upper', 'ExpirationPut', 'ExpirationCall', 'Capital', 'MaxLossPLUnRealized', 'MaxLossPLRealized'])

    final_df = final_df.sort_values(by=['Lower', 'Upper', 'ExpirationPut', 'ExpirationCall', 'Capital', 'MaxLossPLUnRealized', 'MaxLossPLRealized'])

    final_df.to_csv('TrackingAnalizer.csv', index=False)

#expirationDaysPut = [3, 6, 11, 19, 32, 53, 87, 142, 230, 372]

def visualize_tracking_data():
    df = pd.read_csv('TrackingAnalizer.csv')
    
    agg_df = df.groupby(['Lower', 'Upper'])['Capital'].max().reset_index()

    # Pivot the DataFrame
    pivot_df = agg_df.pivot(index='Lower', columns='Upper', values='Capital')

    # Plot the heatmap
    plt.figure(figsize=(10, 8))
    sns.heatmap(pivot_df, cmap='YlGnBu')
    plt.title('Heatmap of Capital by Lower and Upper')
    plt.show()

analyze_tracking_data()
visualize_tracking_data()
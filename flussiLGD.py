import csv

# Read output.csv into a dictionary for quick lookup
output_dict = {}
with open('output.csv', 'r') as f:
    reader = csv.reader(f, delimiter=';')
    for row in reader:
        if row[0] and row[1]:  # Check that the strings are not empty
            output_dict[row[2]] = (int(row[0]), int(row[1]))

# Open modified_flussi_lgd_3.0.csv for reading and writing
with open('modified_flussi_lgd_3.0.csv', 'r') as f:
    rows = list(csv.reader(f, delimiter=';'))

with open('modified_flussi_lgd_3.0.csv', 'w', newline='') as f:
    writer = csv.writer(f, delimiter=';')
    for row in rows:
        fifth_col = row[4]
        if fifth_col in output_dict:
            first_col, second_col = output_dict[fifth_col]
            if first_col < 200712 and second_col == 202312:
                row.append('RUNNING')
            else:
                row.append('NO')
        else:
            row.append('NO')
        writer.writerow(row)
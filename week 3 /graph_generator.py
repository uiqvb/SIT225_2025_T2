import pandas as pd
import matplotlib.pyplot as plt
import os

# === CONFIGURATION ===
csv_filename = "humidity_temp_data.csv"  # Change this to your file name
timestamp_column = "timestamp"           # Name of the timestamp column

# === CHECK FILE EXISTS ===
if not os.path.exists(csv_filename):
    print(f"❌ File not found: {csv_filename}")
    exit()

# === READ CSV ===
df = pd.read_csv(csv_filename)

# === PARSE TIMESTAMP ===
if timestamp_column not in df.columns:
    print(f"❌ Column '{timestamp_column}' not found in CSV.")
    exit()

df[timestamp_column] = pd.to_datetime(df[timestamp_column])

# === PLOT EACH NUMERIC COLUMN ===
for column in df.columns:
    if column == timestamp_column:
        continue
    if pd.api.types.is_numeric_dtype(df[column]):
        plt.figure()
        plt.plot(df[timestamp_column], df[column], label=column)
        plt.xlabel("Timestamp")
        plt.ylabel(column.capitalize())
        plt.title(f"{column.capitalize()} over Time")
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.tight_layout()
        plt.legend()
        plt.show()

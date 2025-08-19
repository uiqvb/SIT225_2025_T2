import pandas as pd
import matplotlib.pyplot as plt
from google.colab import files

# Upload your CSV file
uploaded = files.upload()

# Use the correct file name (exactly as uploaded)
CSV_FILE = "gyroscope_data.csv"  # <-- match the uploaded file name

# Load the CSV
df = pd.read_csv(CSV_FILE)

# Convert timestamp to datetime
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

# Drop rows with invalid timestamps
df = df.dropna(subset=["timestamp"])

# Plot X, Y, Z vs timestamp
plt.figure(figsize=(12, 6))
plt.plot(df["timestamp"], df["x"], label="Gyro X")
plt.plot(df["timestamp"], df["y"], label="Gyro Y")
plt.plot(df["timestamp"], df["z"], label="Gyro Z")

plt.title("Gyroscope Data Over Time")
plt.xlabel("Timestamp")
plt.ylabel("Gyroscope Reading")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

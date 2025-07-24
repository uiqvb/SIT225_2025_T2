import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Configuration
LOG_FILE = "accel_data_20250723.csv"  # Replace with your actual filename
GRAPH_FILE = LOG_FILE.replace('.csv', '.png')

try:
    # Read the CSV file
    df = pd.read_csv(LOG_FILE)

    # Convert timestamp to datetime if needed (depends on your logging format)
    # Option 1: If timestamp is already in datetime format (e.g., "2025-07-23 17:42:07.123")
    df['datetime'] = pd.to_datetime(df['timestamp'])

    # Option 2: If timestamp is in seconds since start (uncomment if needed)
    # df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')  # Convert seconds to datetime

    # Create the plot
    plt.figure(figsize=(12, 8))

    # X-Axis Data
    x_data = df['datetime']  # Use actual timestamps

    # Plot X, Y, Z accelerations
    plt.subplot(3, 1, 1)
    plt.plot(x_data, df['x'], 'r-', linewidth=1)
    plt.ylabel('X (g)')
    plt.title(f'Accelerometer Data ({LOG_FILE})')
    plt.grid(True, linestyle='--', alpha=0.6)

    plt.subplot(3, 1, 2)
    plt.plot(x_data, df['y'], 'g-', linewidth=1)
    plt.ylabel('Y (g)')
    plt.grid(True, linestyle='--', alpha=0.6)

    plt.subplot(3, 1, 3)
    plt.plot(x_data, df['z'], 'b-', linewidth=1)
    plt.ylabel('Z (g)')
    plt.xlabel('Timestamp')
    plt.grid(True, linestyle='--', alpha=0.6)

    # Auto-format date labels
    plt.gcf().autofmt_xdate()

    # Adjust layout and save
    plt.tight_layout()
    plt.savefig(GRAPH_FILE, dpi=300)
    print(f"Graph saved to: {GRAPH_FILE}")

    # Show the plot
    plt.show()

except FileNotFoundError:
    print(f"Error: File '{LOG_FILE}' not found. Please check the filename.")
except Exception as e:
    print(f"Error generating graph: {str(e)}")

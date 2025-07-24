import serial
import time
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

# Configure these
PORT = 'COM14'  # Change to your COM port
LOG_FILE = f"accel_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

try:
    ser = serial.Serial(PORT, 9600, timeout=1)
    print(f"Connected to {PORT}. Logging to {LOG_FILE}")

    with open(LOG_FILE, 'w') as f:
        f.write("timestamp,x,y,z\n")  # CSV header

        while True:
            try:
                line = ser.readline().decode().strip()
                if line and line.count(',') == 2:  # Valid X,Y,Z data
                    current_time = datetime.now()  # Get current datetime object
                    timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Format with milliseconds
                    clean_line = line.replace(" ", "")
                    f.write(f"{timestamp_str},{clean_line}\n")
                    f.flush()  # Force write to disk
                    print(f"Logged: {timestamp_str} - {clean_line}")
            except UnicodeDecodeError:
                continue  # Skip corrupted serial data

except KeyboardInterrupt:
    print("\nLogging stopped.")
except Exception as e:
    print(f"Error: {str(e)}")
finally:
    if 'ser' in locals():
        ser.close()

    # After logging is complete, plot the data
    try:
        print("\nCreating graph from logged data...")
        df = pd.read_csv(LOG_FILE)

        # Convert timestamp string to datetime objects for plotting
        df['datetime'] = pd.to_datetime(df['timestamp'])

        plt.figure(figsize=(12, 6))

        plt.subplot(3, 1, 1)
        plt.plot(df['datetime'], df['x'], 'r-')
        plt.ylabel('X (g)')
        plt.title('Accelerometer Data Over Time')

        plt.subplot(3, 1, 2)
        plt.plot(df['datetime'], df['y'], 'g-')
        plt.ylabel('Y (g)')

        plt.subplot(3, 1, 3)
        plt.plot(df['datetime'], df['z'], 'b-')
        plt.ylabel('Z (g)')
        plt.xlabel('Time')

        # Format x-axis to show readable timestamps
        plt.gcf().autofmt_xdate()  # Auto-rotate date labels

        plt.tight_layout()

        # Save the plot
        plot_file = LOG_FILE.replace('.csv', '.png')
        plt.savefig(plot_file)
        print(f"Graph saved to {plot_file}")

        # Show the plot
        plt.show()

    except Exception as e:
        print(f"Error creating graph: {str(e)}")

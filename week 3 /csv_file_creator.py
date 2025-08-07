import sys
import traceback
from arduino_iot_cloud import ArduinoCloudClient
from datetime import datetime
import csv

# Your Device credentials from Arduino IoT Cloud
DEVICE_ID = "e057c8de-9437-4f08-ab15-b1760419cf64"
SECRET_KEY = "F9R@jPjW0rOaoe?w2DFLI1rjf"

# Open CSV file for writing
csv_file = open("humidity_temp_data.csv", mode="a", newline="")
csv_writer = csv.writer(csv_file)
csv_writer.writerow(["timestamp", "humidity", "temperature"])

# Shared dictionary to hold the latest values
sensor_data = {"humid": None, "temp": None}

# Callback functions
def on_humid_changed(client, value):
    sensor_data["humid"] = value
    write_to_csv()

def on_temp_changed(client, value):
    sensor_data["temp"] = value
    write_to_csv()

# Write row to CSV when both values are available
def write_to_csv():
    if all(v is not None for v in sensor_data.values()):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        csv_writer.writerow([
            timestamp,
            sensor_data["humid"],
            sensor_data["temp"]
        ])
        csv_file.flush()
        print(f"{timestamp} | Humidity: {sensor_data['humid']}%, Temperature: {sensor_data['temp']}°C")
        # Reset values to wait for the next full set
        sensor_data["humid"] = sensor_data["temp"] = None

# Main function
def main():
    print("Starting humidity & temperature data collection...")

    # Instantiate the client
    client = ArduinoCloudClient(
        device_id=DEVICE_ID,
        username=DEVICE_ID,
        password=SECRET_KEY
    )

    # Register variables EXACTLY as named in Arduino IoT Cloud
    client.register("humid", value=None, on_write=on_humid_changed)
    client.register("temp", value=None, on_write=on_temp_changed)

    # Start the client loop (runs forever)
    client.start()

# Exception handling
if __name__ == "__main__":
    try:
        main()
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        print("An error occurred:")
        traceback.print_exception(exc_type, exc_value, exc_traceback)

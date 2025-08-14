import serial
import csv
import time

SERIAL_PORT = 'COM14'  # Your Arduino's serial port
BAUD_RATE = 9600

csv_filename = f"gyro_data_{time.strftime('%Y%m%d_%H%M%S')}.csv"


def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return

    with open(csv_filename, mode='w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['timestamp_ms', 'gyro_x', 'gyro_y', 'gyro_z'])

        print("Reading data... Press Ctrl+C to stop.")
        try:
            while True:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    parts = line.split(',')
                    if len(parts) == 4:
                        timestamp, x, y, z = parts
                        print(f"{timestamp}, {x}, {y}, {z}")
                        csv_writer.writerow([timestamp, x, y, z])
                    else:
                        print(f"Unexpected data format: {line}")
        except KeyboardInterrupt:
            print("\nStopped by user.")
        finally:
            ser.close()
            print(f"Data saved to {csv_filename}")


if __name__ == '__main__':
    main()

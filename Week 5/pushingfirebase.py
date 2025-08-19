import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import serial
import time
import re

# Firebase setup
cred = credentials.Certificate("Manit.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://manitfire-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

ref = db.reference('Manit/Gyroscope')

# Serial setup
ser = serial.Serial('COM16', 9600)
time.sleep(2)

print("Listening to Arduino (Press Ctrl+C to stop)...")

try:
    while True:
        line = ser.readline().decode('utf-8').strip()
        match = re.match(r"x:([-+]?[0-9]\.?[0-9]+),y:([-+]?[0-9]\.?[0-9]+),z:([-+]?[0-9]*\.?[0-9]+)", line)
        if match:
            x, y, z = map(float, match.groups())
            timestamp = datetime.now().isoformat()
            data = {
                "sensor_name": "Gyroscope",
                "timestamp": timestamp,
                "data": {"x": x, "y": y, "z": z}
            }
            ref.push(data)
            print(data)
except KeyboardInterrupt:
    ser.close()
    print("Serial read stopped.")

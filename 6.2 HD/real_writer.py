import csv
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import serial

# ---- fixed config ----
PORT = r"\\.\COM14"      # hard-coded COM port (use \\.\ form for COM10+)
BAUD = 115200            # must match Arduino sketch Serial.begin
OUTDIR = "./data"
ROWS_PER_FILE = 500
PREFIX = "gyro"
PRINT_EVERY = 50
# -----------------------

outdir = Path(OUTDIR)
outdir.mkdir(parents=True, exist_ok=True)

col_x = f"{PREFIX}_x"
col_y = f"{PREFIX}_y"
col_z = f"{PREFIX}_z"

try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)  # wait for Arduino reset
except Exception as e:
    print(f"ERROR: could not open serial port {PORT}: {e}", file=sys.stderr)
    sys.exit(2)

print(f"Connected to {PORT} at {BAUD} baud")
print(f"Writing CSV chunks of {ROWS_PER_FILE} rows to: {outdir.resolve()}")

sample_total = 0
rows_buffer = []


def flush_buffer():
    global rows_buffer
    if not rows_buffer:
        return
    df = pd.DataFrame(rows_buffer, columns=["sample", "timestamp", col_x, col_y, col_z])
    fname = f"{PREFIX}_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    path = outdir / fname
    df.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"Wrote {path} ({len(df)} rows).")
    rows_buffer = []


try:
    ser.reset_input_buffer()
    while True:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) != 3:
            continue
        try:
            x = float(parts[0].strip())
            y = float(parts[1].strip())
            z = float(parts[2].strip())
        except ValueError:
            continue

        ts_iso = datetime.now().isoformat(timespec="milliseconds")
        rows_buffer.append([sample_total, ts_iso, x, y, z])
        sample_total += 1

        if sample_total % PRINT_EVERY == 0:
            print(f"Read {sample_total} samples...")

        if len(rows_buffer) >= ROWS_PER_FILE:
            flush_buffer()

except KeyboardInterrupt:
    print("\nStopping. Flushing any remaining samples...")
    flush_buffer()
except Exception as e:
    print(f"\nERROR: {e}", file=sys.stderr)
    flush_buffer()
finally:
    ser.close()

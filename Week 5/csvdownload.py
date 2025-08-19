import csv
import firebase_admin
from firebase_admin import credentials, db

# === Update these ===
CRED_FILE = "MANIT.json"  # put your downloaded service account JSON filename here
DB_URL = "https://manitfire-default-rtdb.asia-southeast1.firebasedatabase.app/"
DB_PATH = "Manit/Gyroscope"  # change if your path is different
CSV_NAME = "gyroscope_data.csv"


def setup_firebase():
    """Start Firebase app if not already started."""
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(CRED_FILE)
        firebase_admin.initialize_app(cred, {"databaseURL": DB_URL})


def get_snapshot():
    """Read data from the database path."""
    ref = db.reference(DB_PATH)
    return ref.get()  # returns dict or None


def save_csv(rows):
    """Write out rows to CSV with required header."""
    with open(CSV_NAME, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "x", "y", "z"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main():
    setup_firebase()

    data = get_snapshot()

    # If nothing in DB, still create the CSV with just the header
    if not data:
        with open(CSV_NAME, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "x", "y", "z"])
        print("Data written to gyroscope_data.csv")
        return

    # Build clean rows; skip any malformed entries
    out_rows = []
    for item in data.values():
        try:
            ts = item["timestamp"]
            x = item["data"]["x"]
            y = item["data"]["y"]
            z = item["data"]["z"]
        except (TypeError, KeyError):
            continue
        out_rows.append({"timestamp": ts, "x": x, "y": y, "z": z})

    save_csv(out_rows)
    print("Data written to gyroscope_data.csv")


if __name__ == "__main__":
    main()

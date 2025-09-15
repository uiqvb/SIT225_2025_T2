# task8_2c_dash_smooth.py
# SIT225 8.2C — smooth Dash updates for smartphone accelerometer (X, Y, Z)
# Uses smoothdash.make_smooth_app + Arduino IoT Cloud callbacks.
# Adds: background saver to ./data 2 + "Force Save Now" button in the UI.

from datetime import datetime
import threading
import time
from pathlib import Path
import csv

from arduino_iot_cloud import ArduinoCloudClient
from iot_secrets import DEVICE_ID, SECRET_KEY
from smoothdash import make_smooth_app

import plotly.graph_objects as go
from dash import html, dcc, Output, Input

# ------------------ User config ------------------
VAR_X = "accelerometer_x"
VAR_Y = "accelerometer_y"
VAR_Z = "accelerometer_z"

WINDOW_POINTS = 600
MAX_APPEND    = 15
POLL_MS       = 150

# Save sooner so you can see files appear quickly
SAVE_EVERY_SEC     = 5           # was 10
MIN_POINTS_TO_SAVE = 30          # was 120
OUTPUT_PREFIX      = "accel"

DATA_DIR = (Path(__file__).resolve().parent / "data 2")
DATA_DIR.mkdir(parents=True, exist_ok=True)
# -------------------------------------------------

# Build the app and get the thread-safe push() to feed samples
app, state = make_smooth_app(
    ["X", "Y", "Z"],
    window_points=WINDOW_POINTS,
    max_append=MAX_APPEND,
    poll_ms=POLL_MS,
)
push = state["push"]

# --- Add a "Force Save Now" button + status text to layout ---
if isinstance(app.layout, (list, tuple)):
    base_children = list(app.layout)
else:
    # assume it's an html.Div
    base_children = list(app.layout.children) if hasattr(app.layout, "children") else []

control_bar = html.Div([
    html.Button("Force Save Now", id="force-save-btn", n_clicks=0, style={"marginRight": "12px"}),
    html.Span("Status: ", style={"fontWeight": "600"}),
    html.Span(id="save-status", children="Waiting for data…"),
    dcc.Interval(id="save-log-interval", interval=3000, n_intervals=0),  # print buffer info periodically
], style={"padding": "8px 12px", "borderTop": "1px solid #ddd", "marginTop": "8px"})

if hasattr(app, "layout") and hasattr(app.layout, "children"):
    app.layout.children = [*base_children, control_bar]
else:
    app.layout = html.Div([*base_children, control_bar])

# Collect full (x, y, z) trios from Cloud, then push(ts, x, y, z)
latest = {"x": None, "y": None, "z": None}
seen   = {"x": False, "y": False, "z": False}
lock = threading.Lock()

# Logging buffer for saving
log_lock = threading.Lock()
log_rows = []  # list of tuples: (iso_ts, x, y, z)

def _now_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _try_emit():
    # lock must be held
    if seen["x"] and seen["y"] and seen["z"]:
        x, y, z = latest["x"], latest["y"], latest["z"]

        ts_hms = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # pretty for UI
        push(ts_hms, x, y, z)

        ts_iso = datetime.now().isoformat(timespec="milliseconds")
        with log_lock:
            log_rows.append((ts_iso, x, y, z))

        seen["x"] = seen["y"] = seen["z"] = False

def on_x(_client, v):
    with lock:
        latest["x"] = float(v) if v is not None else None
        seen["x"] = True
        _try_emit()

def on_y(_client, v):
    with lock:
        latest["y"] = float(v) if v is not None else None
        seen["y"] = True
        _try_emit()

def on_z(_client, v):
    with lock:
        latest["z"] = float(v) if v is not None else None
        seen["z"] = True
        _try_emit()

def start_cloud_thread():
    client = ArduinoCloudClient(device_id=DEVICE_ID, username=DEVICE_ID, password=SECRET_KEY)
    client.register(VAR_X, value=None, on_write=on_x)
    client.register(VAR_Y, value=None, on_write=on_y)
    client.register(VAR_Z, value=None, on_write=on_z)

    def run():
        print("[Cloud] Connecting… keep the phone app in FOREGROUND with accelerometer ON.")
        client.start()

    th = threading.Thread(target=run, daemon=True)
    th.start()
    return th

def _save_csv(rows, base_path: Path) -> Path:
    csv_path = base_path.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "x", "y", "z"])
        w.writerows(rows)
    return csv_path

def _save_png_or_html(rows, base_path: Path):
    ts = [r[0] for r in rows]
    xs = [r[1] for r in rows]
    ys = [r[2] for r in rows]
    zs = [r[3] for r in rows]

    fig = go.Figure()
    fig.add_scatter(x=ts, y=xs, mode="lines", name="X")
    fig.add_scatter(x=ts, y=ys, mode="lines", name="Y")
    fig.add_scatter(x=ts, y=zs, mode="lines", name="Z")
    fig.update_layout(
        title=f"Accelerometer window — saved {base_path.name}",
        xaxis_title="time",
        yaxis_title="accel",
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(orientation="h", y=1.02, x=0),
        template="plotly_white",
    )

    png_path  = base_path.with_suffix(".png")
    html_path = base_path.with_suffix(".html")
    try:
        fig.write_image(str(png_path), width=1200, height=500, scale=2)  # needs kaleido
        return ("png", png_path)
    except Exception as e:
        fig.write_html(str(html_path), include_plotlyjs="cdn")
        return ("html", html_path)

def _save_batch(rows):
    base = DATA_DIR / f"{OUTPUT_PREFIX}_{_now_stamp()}"
    csv_path = _save_csv(rows, base)
    kind, art_path = _save_png_or_html(rows, base)
    print(f"[Save] {len(rows)} samples | CSV -> {csv_path.name} | {kind.upper()} -> {art_path.name}")
    return f"Saved {len(rows)} samples: {csv_path.name} + {art_path.name}"

def start_autosave_thread():
    def run():
        while True:
            time.sleep(SAVE_EVERY_SEC)
            with log_lock:
                n = len(log_rows)
                if n >= MIN_POINTS_TO_SAVE:
                    rows = log_rows[:]
                    log_rows.clear()
                else:
                    rows = []
            if rows:
                _ = _save_batch(rows)
            else:
                print(f"[Save] Skipped: only {n} buffered (< {MIN_POINTS_TO_SAVE}).")
    th = threading.Thread(target=run, daemon=True)
    th.start()
    return th

# --- Dash callbacks for the force-save button and status ---
@app.callback(
    Output("save-status", "innerText"),
    Input("force-save-btn", "n_clicks"),
    prevent_initial_call=True,
)
def force_save(_n):
    with log_lock:
        n = len(log_rows)
        if n == 0:
            return "No data buffered yet — move the phone with the IoT app in foreground."
        rows = log_rows[:]
        log_rows.clear()
    msg = _save_batch(rows)
    return msg

@app.callback(
    Output("save-status", "title"),
    Input("save-log-interval", "n_intervals"),
)
def show_buffer_size(_n):
    with log_lock:
        n = len(log_rows)
    # also print periodically so you can see progress in terminal
    print(f"[Buffer] {n} samples buffered")
    return f"Buffered: {n} samples"

if __name__ == "__main__":
    start_cloud_thread()
    start_autosave_thread()
    print(f"Saving to: {DATA_DIR}")
    print("Dash at http://127.0.0.1:8050")
    app.run(debug=False, host="127.0.0.1", port=8050)

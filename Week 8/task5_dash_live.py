# task5_dash_live.py
# SIT225 8.1P — Live Plotly Dash viewer with dual buffers and autosave
#
# How to use:
# 1) pip install arduino-iot-cloud dash plotly pandas kaleido
# 2) Put your secrets in iot_secrets.py (DEVICE_ID, SECRET_KEY)
# 3) Ensure Python Thing variables are accelerometer_x/y/z and linked to phone Thing.
# 4) Run:  python task5_dash_live.py  → open http://127.0.0.1:8050
#
from pathlib import Path
from datetime import datetime
import threading
from collections import deque

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Output, Input

from arduino_iot_cloud import ArduinoCloudClient
from iot_secrets import DEVICE_ID, SECRET_KEY

# ---- Config ----
VAR_X = "accelerometer_x"
VAR_Y = "accelerometer_y"
VAR_Z = "accelerometer_z"

SAMPLES_PER_WINDOW = 5      # ~10s at ~50 Hz; adjust for your rate
DASH_REFRESH_MS = 1000        # check every 1s for a fresh N-sample batch

ROOT = Path(__file__).resolve().parent
PLOT_DIR = ROOT / "plots"
PLOT_DIR.mkdir(parents=True, exist_ok=True)

# ---- Buffers & state ----
inbox = deque()          # receives (ts_str, x, y, z)
inbox_lock = threading.Lock()

latest = {"x": None, "y": None, "z": None}
seen   = {"x": False, "y": False, "z": False}
state_lock = threading.Lock()

last_batch = []
last_save_name = None

# ---- Cloud callbacks ----
def _append_if_full_trio():
    # Called while holding state_lock
    if seen["x"] and seen["y"] and seen["z"]:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        row = (ts, latest["x"], latest["y"], latest["z"])
        with inbox_lock:
            inbox.append(row)
        seen["x"] = seen["y"] = seen["z"] = False

def on_x(_client, value):
    with state_lock:
        latest["x"] = float(value) if value is not None else None
        seen["x"] = True
        _append_if_full_trio()

def on_y(_client, value):
    with state_lock:
        latest["y"] = float(value) if value is not None else None
        seen["y"] = True
        _append_if_full_trio()

def on_z(_client, value):
    with state_lock:
        latest["z"] = float(value) if value is not None else None
        seen["z"] = True
        _append_if_full_trio()

def start_cloud_thread():
    client = ArduinoCloudClient(
        device_id=DEVICE_ID,
        username=DEVICE_ID,
        password=SECRET_KEY,
    )
    client.register(VAR_X, value=None, on_write=on_x)
    client.register(VAR_Y, value=None, on_write=on_y)
    client.register(VAR_Z, value=None, on_write=on_z)

    def runner():
        try:
            print("[Cloud] Connecting… keep the phone app in foreground.")
            client.start()
        except Exception as e:
            print("[Cloud] Error:", e)

    th = threading.Thread(target=runner, daemon=True)
    th.start()
    return th

# ---- Dash app ----
app = Dash(__name__)
app.layout = html.Div(
    style={"fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, Arial", "padding": "12px"},
    children=[
        html.H2("SIT225 8.1P — Live Accelerometer (X/Y/Z)"),
        html.Div(id="stats", style={"marginBottom": "8px"}),
        dcc.Graph(id="accel_graph"),
        dcc.Interval(id="poller", interval=DASH_REFRESH_MS, n_intervals=0),
        html.Div("If images don’t save, install 'kaleido' (pip install kaleido).", style={"fontSize": "12px", "opacity": 0.7}),
    ]
)

def draw_figure(batch):
    if not batch:
        fig = go.Figure()
        fig.update_layout(template="plotly_white",
                          margin=dict(l=40, r=20, t=40, b=40),
                          xaxis_title="Time", yaxis_title="Acceleration (g)",
                          title="Waiting for data…")
        return fig
    ts, xs, ys, zs = zip(*batch)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(ts), y=list(xs), mode="lines", name="X"))
    fig.add_trace(go.Scatter(x=list(ts), y=list(ys), mode="lines", name="Y"))
    fig.add_trace(go.Scatter(x=list(ts), y=list(zs), mode="lines", name="Z"))
    fig.update_layout(template="plotly_white",
                      margin=dict(l=40, r=20, t=40, b=40),
                      xaxis_title="Time", yaxis_title="Acceleration (g)",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      title=f"Latest window (N={len(batch)})")
    return fig

def save_outputs(batch, fig):
    global last_save_name
    if not batch:
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"accel_{stamp}"

    # CSV
    df = pd.DataFrame(batch, columns=["timestamp","x","y","z"])
    csv_path = PLOT_DIR / f"{base}.csv"
    df.to_csv(csv_path, index=False)

    # Figure
    png_path = PLOT_DIR / f"{base}.png"
    html_path = PLOT_DIR / f"{base}.html"
    try:
        # Requires kaleido; if not installed, fallback to HTML
        fig.write_image(str(png_path), width=1200, height=500, scale=2)
        last_save_name = png_path.name
    except Exception:
        fig.write_html(str(html_path), include_plotlyjs="cdn")
        last_save_name = html_path.name
    return last_save_name

@app.callback(
    Output("accel_graph", "figure"),
    Output("stats", "children"),
    Input("poller", "n_intervals"),
    prevent_initial_call=False
)
def refresh(_n):
    global last_batch
    with inbox_lock:
        if len(inbox) >= SAMPLES_PER_WINDOW:
            batch = [inbox.popleft() for _ in range(SAMPLES_PER_WINDOW)]
        else:
            batch = None

    if batch is None:
        fig = draw_figure(last_batch)
        return fig, f"Waiting… inbox={len(inbox)}, last_save={last_save_name or '—'}"

    last_batch = batch
    fig = draw_figure(batch)
    saved = save_outputs(batch, fig)
    return fig, f"Saved: {saved} | inbox now {len(inbox)}"

def main():
    start_cloud_thread()
    print("Dash running at http://127.0.0.1:8050")
    app.run(debug=False, host="127.0.0.1", port=8050)  # Dash 3+

if __name__ == "__main__":
    main()

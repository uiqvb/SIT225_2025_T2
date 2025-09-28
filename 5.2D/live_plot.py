#!/usr/bin/env python3
import json
from collections import deque
from datetime import datetime, timezone

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import paho.mqtt.client as mqtt
import config  # uses your MQTT_* settings

# -------- settings you can tweak --------
WINDOW_SECONDS = 30          # rolling window on the x-axis
MAX_POINTS = 1200            # ring buffer cap to avoid huge memory
CSV_PATH = None              # e.g. "live_samples.csv" to save as you stream
REDRAW_MS = 200              # refresh rate of the plot in milliseconds
# ----------------------------------------

# ring buffers
t = deque(maxlen=MAX_POINTS)
xv = deque(maxlen=MAX_POINTS)
yv = deque(maxlen=MAX_POINTS)
zv = deque(maxlen=MAX_POINTS)

t0 = None  # start time (set on first sample)

def ts_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

# ---------- Matplotlib figure ----------
plt.rcParams["figure.autolayout"] = True
fig, axs = plt.subplots(2, 2, figsize=(11, 7))
ax_x, ax_y, ax_z, ax_all = axs.ravel()

ln_x, = ax_x.plot([], [], label="X")
ln_y, = ax_y.plot([], [], label="Y")
ln_z, = ax_z.plot([], [], label="Z")
ln_all_x, = ax_all.plot([], [], label="X")
ln_all_y, = ax_all.plot([], [], label="Y")
ln_all_z, = ax_all.plot([], [], label="Z")

for ax, title in zip(
    (ax_x, ax_y, ax_z, ax_all),
    ("Gyroscope X", "Gyroscope Y", "Gyroscope Z", "Gyroscope X,Y,Z Combined"),
):
    ax.set_title(title)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Value")
    ax.grid(True)

ax_all.legend(loc="upper right")

def on_key(event):
    if event.key == "s":
        fname = f"live_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        fig.savefig(fname, dpi=150)
        print(f"📸 Saved snapshot: {fname}")
fig.canvas.mpl_connect("key_press_event", on_key)

def redraw(_):
    if not t:
        return
    # keep a rolling window
    tmax = t[-1]
    tmin = max(0.0, tmax - WINDOW_SECONDS)
    for ax in (ax_x, ax_y, ax_z, ax_all):
        ax.set_xlim(tmin, max(WINDOW_SECONDS, tmax))

    ln_x.set_data(t, xv); ax_x.relim(); ax_x.autoscale_view(True, True, True)
    ln_y.set_data(t, yv); ax_y.relim(); ax_y.autoscale_view(True, True, True)
    ln_z.set_data(t, zv); ax_z.relim(); ax_z.autoscale_view(True, True, True)

    ln_all_x.set_data(t, xv)
    ln_all_y.set_data(t, yv)
    ln_all_z.set_data(t, zv)
    ax_all.relim(); ax_all.autoscale_view(True, True, True)

# ---------- MQTT callbacks (Paho v2) ----------
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("✅ Connected to HiveMQ")
        client.subscribe(config.MQTT_TOPIC, qos=1)
        print(f"📡 Subscribed to: {config.MQTT_TOPIC}")
    else:
        print(f"❌ MQTT connect failed (code={reason_code})")

def on_message(client, userdata, msg):
    global t0
    try:
        payload = msg.payload.decode("utf-8", errors="replace").strip()
        data = json.loads(payload)  # expect {"x":..,"y":..,"z":..}

        x = float(data["x"]); y = float(data["y"]); z = float(data["z"])

        now = datetime.now(timezone.utc)
        if t0 is None:
            t0 = now
        elapsed = (now - t0).total_seconds()

        t.append(elapsed); xv.append(x); yv.append(y); zv.append(z)

        if CSV_PATH:
            with open(CSV_PATH, "a", encoding="utf-8") as f:
                f.write(f"{ts_iso()},{x},{y},{z}\n")

    except Exception as e:
        print(f"⚠️ Bad message: {e} | raw: {msg.payload[:120]}")

def on_disconnect(client, userdata, reason_code, properties=None):
    print(f"🔌 Disconnected (code={reason_code})")

# ---------- MQTT client ----------
mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.username_pw_set(config.MQTT_USER, config.MQTT_PASS)
mqtt_client.tls_set()  # HiveMQ Cloud requires TLS
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.on_disconnect = on_disconnect

print("🚀 Connecting to HiveMQ…")
mqtt_client.connect(config.MQTT_BROKER, int(config.MQTT_PORT), keepalive=60)

# run MQTT loop in the background so the UI stays responsive
mqtt_client.loop_start()
ani = animation.FuncAnimation(fig, redraw, interval=REDRAW_MS, blit=False)

try:
    plt.show()
finally:
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

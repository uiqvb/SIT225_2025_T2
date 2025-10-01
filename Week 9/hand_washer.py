import json, time, argparse
import serial, pandas as pd
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument("--port", required=True)  # e.g. COM6 or /dev/ttyACM0
parser.add_argument("--baud", type=int, default=115200)
parser.add_argument("--out", default="handwash_log.csv")
args = parser.parse_args()

ser = serial.Serial(args.port, args.baud, timeout=1)
rows = []
print("Connected to", args.port)

plt.ion()
fig, ax = plt.subplots(figsize=(9,4))
ln, = ax.plot([], [])
ax.set_xlabel("sample #")
ax.set_ylabel("distance (cm)")
ax.set_ylim(0, 80)

try:
    while True:
        line = ser.readline().decode("utf-8", "ignore").strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except:
            continue
        rows.append(o)
        if len(rows) % 10 == 0:
            # live plot last 300 points
            d = [r.get("distance_cm",-1) for r in rows[-300:]]
            ln.set_data(range(len(d)), d)
            ax.set_xlim(0, max(50, len(d)))
            fig.canvas.draw(); fig.canvas.flush_events()
            # print event summaries
            evt = o.get("event","none")
            if evt == "end":
                print(f"Detected wash event, duration: {o.get('dur_s',0):.1f}s")
except KeyboardInterrupt:
    pass
finally:
    if rows:
        pd.DataFrame(rows).to_csv(args.out, index=False)
        print("Saved", args.out)

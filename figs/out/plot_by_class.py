# plot_by_class.py
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).parent.resolve()

# Prefer CSV in the same folder as this script; otherwise try CWD
csv_candidates = [
    HERE / "table_by_class.csv",
    Path.cwd() / "table_by_class.csv",
    HERE.parent / "table_by_class.csv",
]

csv_path = next((p for p in csv_candidates if p.exists()), None)
if not csv_path:
    raise FileNotFoundError("table_by_class.csv not found near script or CWD. "
                            "Run analyze_handwash.py first and check paths.")

df = pd.read_csv(csv_path)

# Output directory = same folder as this script
outdir = HERE
outdir.mkdir(parents=True, exist_ok=True)

# 1) Bar chart: mean duration by class
plt.figure(figsize=(6,4))
plt.bar(df["label"], df["mean_s"])
plt.xlabel("Class")
plt.ylabel("Mean duration (s)")
plt.title("Mean Handwash Duration by Class")
plt.tight_layout()
plt.savefig(outdir / "byclass_mean_duration.png")
plt.close()

# 2) Bar chart: >=20s compliance by class
plt.figure(figsize=(6,4))
plt.bar(df["label"], df["ge20_pct"])
plt.xlabel("Class")
plt.ylabel("≥20s compliance (%)")
plt.title("Compliance (≥20s) by Class")
plt.tight_layout()
plt.savefig(outdir / "byclass_compliance.png")
plt.close()

print("Saved:",
      (outdir / "byclass_mean_duration.png").name,
      (outdir / "byclass_compliance.png").name)

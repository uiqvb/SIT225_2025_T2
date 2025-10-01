import argparse, os, re, pandas as pd, matplotlib.pyplot as plt
from pathlib import Path


def load_csvs(paths):
    files = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            files += sorted([f for f in p.glob("*.csv")])
        elif p.suffix.lower() == ".csv":
            files.append(p)
    return files


def class_from_name(name):
    n = name.lower()
    if "quick" in n or "rinse" in n: return "quick_rinse"
    if "proper" in n or "wash" in n: return "proper_wash"
    return "unlabeled"


def summarize_file(path):
    df = pd.read_csv(path)
    ends = df[df.get("event", "") == "end"].copy()
    if ends.empty:
        return {"file": path.name, "events": 0, "avg_s": 0, "median_s": 0, "ge20_pct": 0,
                "label": class_from_name(path.name)}
    dur = ends["dur_s"].astype(float)
    return {
        "file": path.name,
        "events": len(dur),
        "avg_s": round(dur.mean(), 1),
        "median_s": round(dur.median(), 1),
        "ge20_pct": round((dur >= 20).mean() * 100, 1),
        "label": class_from_name(path.name)
    }


def plot_hist(durations, outpng):
    plt.figure(figsize=(7, 4))
    plt.hist(durations, bins=12)
    plt.xlabel("Duration (s)");
    plt.ylabel("Count")
    plt.title("Handwash Duration Distribution")
    plt.tight_layout();
    plt.savefig(outpng);
    plt.close()


def plot_sample_trace(path, outpng):
    df = pd.read_csv(path)
    # show last ~300 samples or whole file if short
    tail = df.tail(300)
    x = (tail["ts"] / 1000.0) if "ts" in tail.columns else range(len(tail))
    y = tail["distance_cm"]
    plt.figure(figsize=(8, 4))
    plt.plot(x, y)
    plt.xlabel("Time (s)");
    plt.ylabel("Distance (cm)")
    plt.title(f"Recent Distance Trace – {Path(path).name}")
    plt.tight_layout();
    plt.savefig(outpng);
    plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inputs", nargs="+", required=True, help="CSV files and/or folders")
    ap.add_argument("--outdir", default="figs", help="Output folder for figures/tables")
    args = ap.parse_args()

    outdir = Path(args.outdir);
    outdir.mkdir(parents=True, exist_ok=True)

    files = load_csvs(args.inputs)
    if not files:
        raise SystemExit("No CSV files found.")

    # Per-file summaries
    rows = [summarize_file(p) for p in files]
    df_sum = pd.DataFrame(rows).sort_values(["label", "file"])
    df_sum.to_csv(outdir / "table_by_file.csv", index=False)

    # Overall metrics (all events)
    all_dur = []
    for p in files:
        df = pd.read_csv(p)
        ends = df[df.get("event", "") == "end"]
        if not ends.empty:
            all_dur += ends["dur_s"].astype(float).tolist()

    if all_dur:
        overall = pd.DataFrame({
            "metric": ["Events", "Avg duration (s)", "Median duration (s)", ">=20s compliance (%)"],
            "value": [len(all_dur), round(pd.Series(all_dur).mean(), 1),
                      round(pd.Series(all_dur).median(), 1),
                      round((pd.Series(all_dur) >= 20).mean() * 100, 1)]
        })
        overall.to_csv(outdir / "table_overall.csv", index=False)
        plot_hist(all_dur, outdir / "duration_hist.png")
    else:
        print("Warning: no completed events found in any file.")

    # By class (if filenames contain quick/proper)
    df_sum.to_csv(outdir / "table_by_file.csv", index=False)
    if "label" in df_sum.columns and not df_sum.empty:
        byclass = df_sum.groupby("label").agg(
            N=("events", "sum"),
            mean_s=("avg_s", "mean"),
            ge20_pct=("ge20_pct", "mean")
        ).reset_index()
        byclass.to_csv(outdir / "table_by_class.csv", index=False)

    # Distance trace from the longest-duration file (nice figure)
    longest = None;
    best = 0
    for p in files:
        df = pd.read_csv(p)
        ends = df[df.get("event", "") == "end"]
        if not ends.empty:
            d = float(ends["dur_s"].max())
            if d > best:
                best = d;
                longest = p
    if longest:
        plot_sample_trace(longest, outdir / "example_trace.png")

    # Console summary for quick copy-paste
    print("\n=== Overall (all files) ===")
    if all_dur:
        print(f"Events: {len(all_dur)}")
        print(f"Avg: {round(pd.Series(all_dur).mean(), 1)} s | Median: {round(pd.Series(all_dur).median(), 1)} s")
        print(f">=20s compliance: {round((pd.Series(all_dur) >= 20).mean() * 100, 1)}%")
    print("\nSaved outputs in:", outdir.resolve())
    for f in ["table_overall.csv", "table_by_class.csv", "table_by_file.csv", "duration_hist.png", "example_trace.png"]:
        p = outdir / f
        if p.exists(): print(" -", p)


if __name__ == "__main__":
    main()

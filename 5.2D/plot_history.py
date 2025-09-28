#!/usr/bin/env python3
"""
Read historical gyro data from MongoDB (and/or Redis) and make report-ready plots:
  1) three stacked subplots (X, Y, Z)
  2) one combined plot (X, Y, Z together)
Also writes a CSV.

Requires: pymongo, redis (optional), pandas, matplotlib
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd
import matplotlib.pyplot as plt

import config

# ---------- Where to save outputs ----------
OUT_DIR = "figures"
CSV_PATH = os.path.join(OUT_DIR, "gyro_history.csv")
PNG_SUBPLOTS = os.path.join(OUT_DIR, "gyro_xyz_subplots.png")
PNG_COMBINED = os.path.join(OUT_DIR, "gyro_xyz_combined.png")

os.makedirs(OUT_DIR, exist_ok=True)


# ---------- Loaders ----------
def load_from_mongo(limit: Optional[int] = None) -> List[Dict]:
    from pymongo import MongoClient
    client = MongoClient(config.MONGO_URI)
    col = client[config.MONGO_DB][config.MONGO_COLLECTION]

    cursor = col.find({}, {"_id": 0}).sort("ts_iso", 1)
    if limit:
        cursor = cursor.limit(limit)
    docs = list(cursor)
    client.close()
    return docs


def load_from_redis(limit: Optional[int] = None) -> List[Dict]:
    # only if Redis creds present in config
    need = ("REDIS_HOST", "REDIS_PORT", "REDIS_USER", "REDIS_PASS")
    if not all(hasattr(config, k) for k in need):
        return []

    import redis

    # Try TLS first, then non-TLS as fallback (Windows OpenSSL quirk)
    def _connect(ssl_flag: bool):
        return redis.Redis(
            host=config.REDIS_HOST,
            port=int(config.REDIS_PORT),
            username=getattr(config, "REDIS_USER", None),
            password=config.REDIS_PASS,
            ssl=ssl_flag,
            ssl_cert_reqs=None if ssl_flag else None,
            socket_timeout=3,
        )

    try:
        r = _connect(True)
        r.ping()
    except Exception:
        r = _connect(False)
        r.ping()

    keys = sorted([k.decode() if isinstance(k, bytes) else k for k in r.keys("*")])
    if limit:
        keys = keys[-limit:]

    docs = []
    for k in keys:
        val = r.get(k)
        if not val:
            continue
        try:
            d = json.loads(val)
            # ensure ordering and types
            docs.append({
                "ts_iso": d.get("ts_iso", k),
                "x": float(d["x"]),
                "y": float(d["y"]),
                "z": float(d["z"]),
            })
        except Exception:
            # skip malformed rows
            continue
    return docs


# ---------- Build DataFrame ----------
def make_dataframe(use_mongo=True, use_redis=False, limit=None) -> pd.DataFrame:
    rows: List[Dict] = []
    if use_mongo:
        rows.extend(load_from_mongo(limit=limit))
    if use_redis:
        rows.extend(load_from_redis(limit=limit))

    if not rows:
        raise RuntimeError("No data found. Make sure Mongo/Redis contain documents.")

    # Remove dupes by (ts_iso, x, y, z) and sort
    df = pd.DataFrame(rows).drop_duplicates().sort_values("ts_iso")
    # Parse timestamp and set index for nice plotting
    df["ts"] = pd.to_datetime(df["ts_iso"], errors="coerce")
    df = df.dropna(subset=["ts"])
    df = df.set_index("ts")
    # Keep only numeric columns
    df = df[["x", "y", "z"]].astype(float)
    return df


# ---------- Plotting ----------
def plot_and_save(df: pd.DataFrame) -> None:
    # 1) Subplots
    fig, axes = plt.subplots(3, 1, figsize=(11, 7), sharex=True)
    axes[0].plot(df.index, df["x"], label="X")
    axes[1].plot(df.index, df["y"], label="Y")
    axes[2].plot(df.index, df["z"], label="Z")
    axes[0].set_title("Gyroscope X")
    axes[1].set_title("Gyroscope Y")
    axes[2].set_title("Gyroscope Z")
    for ax in axes:
        ax.set_ylabel("Value")
        ax.grid(True)
        ax.legend(loc="upper right")
    axes[-1].set_xlabel("Timestamp")
    fig.tight_layout()
    fig.savefig(PNG_SUBPLOTS, dpi=150)
    plt.close(fig)

    # 2) Combined
    fig2, ax = plt.subplots(figsize=(9, 5))
    ax.plot(df.index, df["x"], label="X")
    ax.plot(df.index, df["y"], label="Y")
    ax.plot(df.index, df["z"], label="Z")
    ax.set_title("Gyroscope X, Y, Z Combined")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Value")
    ax.legend(loc="upper right")
    ax.grid(True)
    fig2.tight_layout()
    fig2.savefig(PNG_COMBINED, dpi=150)
    plt.close(fig2)


def to_csv(df: pd.DataFrame) -> None:
    df_out = df.copy()
    df_out.reset_index(names="ts")  # keep ts as a column
    df_out.to_csv(CSV_PATH, index=True, date_format="%Y-%m-%dT%H:%M:%S.%fZ")


if __name__ == "__main__":
    # Choose sources here:
    USE_MONGO = True
    USE_REDIS = False   # set True if you also want to pull from Redis

    # Optional: limit to most recent N samples (None = all)
    LIMIT = None

    print("📥 Loading data…")
    df = make_dataframe(use_mongo=USE_MONGO, use_redis=USE_REDIS, limit=LIMIT)

    print(f"✅ Loaded {len(df)} rows. Writing CSV and plots…")
    to_csv(df)
    plot_and_save(df)

    print(f"📄 CSV:  {CSV_PATH}")
    print(f"🖼  PNG:  {PNG_SUBPLOTS}")
    print(f"🖼  PNG:  {PNG_COMBINED}")
    print("Done.")

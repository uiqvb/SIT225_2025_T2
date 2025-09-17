# streamlit_app.py  (robust + debug view)
from pathlib import Path
import time
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(page_title="Gyroscope Dashboard (Streamlit)", layout="wide")
st.write("✅ App started")

def list_csvs(folder: Path):
    try:
        return sorted(folder.glob("*.csv"), key=lambda p: p.stat().st_mtime)
    except Exception:
        return []

def latest_csv_path(folder: Path):
    files = list_csvs(folder)
    return files[-1] if files else None

def load_csv(p):
    try:
        df = pd.read_csv(p)
        df.columns = [c.strip() for c in df.columns]
        if "sample" not in df.columns:
            df["sample"] = np.arange(len(df))
        return df
    except Exception as e:
        st.error(f"❌ Could not read CSV: {e}")
        return pd.DataFrame()

def get_axis_options(df: pd.DataFrame):
    pref = [c for c in ["gyro_x", "gyro_y", "gyro_z"] if c in df.columns]
    if pref:
        return pref
    return [c for c in df.select_dtypes(include=[np.number]).columns if c != "sample"]

def clamp(v, lo, hi):
    return max(lo, min(int(v), hi))

# --- sidebar controls ---
st.sidebar.title("Controls")
data_mode = st.sidebar.radio("Data source", ["Upload single CSV", "Watch folder for latest CSV"], index=1)

uploaded_df = pd.DataFrame()
watched_df = pd.DataFrame()
current_file_info = ""

if data_mode == "Upload single CSV":
    file = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if file is not None:
        uploaded_df = load_csv(file)
        current_file_info = f"Uploaded file: {file.name}"
else:
    default_folder = str((Path.cwd() / "data").resolve())
    folder_str = st.sidebar.text_input("Folder to watch", value=default_folder)
    # IMPORTANT: strip quotes/spaces so paths like "C:\...\data" work
    folder = Path(folder_str.strip().strip('"').strip("'"))
    st.sidebar.caption(f"Using: {folder}")
    st.write({"watch_folder": str(folder), "exists": folder.exists(),
              "csv_count": len(list(folder.glob('*.csv')))})

    if not folder.exists():
        st.warning("Folder does not exist. Fix the path above.")
    newest = latest_csv_path(folder)
    if newest is not None:
        current_file_info = f"Watching: {folder} • Latest: {newest.name}"
        watched_df = load_csv(newest)
    else:
        st.warning("No CSV files found in the folder yet.")
        watched_df = pd.DataFrame()

# pick active df
df = uploaded_df if data_mode == "Upload single CSV" else watched_df

# show a small preview (even if empty) so the page is never blank
with st.expander("Data preview / status", expanded=True):
    st.write("current_file_info:", current_file_info or "(none)")
    st.write("df shape:", df.shape)
    if not df.empty:
        st.dataframe(df.head(10))
    else:
        st.info("No data yet. Upload a CSV or point to a folder that has *.csv files.")

if df.empty:
    st.stop()

# --- plotting controls ---
chart_type = st.sidebar.selectbox("Chart type", ["Line", "Scatter", "Histogram"], index=0)

axis_options = get_axis_options(df)
if not axis_options:
    st.error("No numeric columns available to plot.")
    st.stop()

axes = st.sidebar.multiselect("Axes to include", axis_options, default=axis_options)
if not axes:
    st.warning("Select at least one axis to plot.")
    st.stop()

# windowing
if "start_idx" not in st.session_state:
    st.session_state.start_idx = 0
if "window_n" not in st.session_state:
    st.session_state.window_n = min(200, len(df))

st.sidebar.subheader("Samples to display")
win_n = st.sidebar.number_input("Number of samples (N)", min_value=10, max_value=int(len(df)),
                                value=min(200, int(len(df))), step=10)
st.session_state.window_n = int(win_n)

c1, c2 = st.sidebar.columns(2)
if c1.button("Previous"):
    st.session_state.start_idx = max(0, st.session_state.start_idx - st.session_state.window_n)
if c2.button("Next"):
    st.session_state.start_idx = min(max(0, len(df) - st.session_state.window_n),
                                     st.session_state.start_idx + st.session_state.window_n)

start = clamp(st.session_state.start_idx, 0, max(0, len(df)-1))
end   = clamp(start + st.session_state.window_n, 1, len(df))
window_df = df.iloc[start:end].copy()

# --- layout ---
st.title("Gyroscope Dashboard — Streamlit")
st.caption("Watch a folder for newest CSV and page through N-sample windows.")
cols = st.columns(3)
cols[0].metric("Total rows", len(df))
cols[1].metric("Window size (N)", st.session_state.window_n)
cols[2].metric("Window range", f"{start}–{end-1}")

if current_file_info:
    st.markdown(f"**Data source:** {current_file_info}")

# long form for altair
long_df = window_df.reset_index(drop=True).reset_index().rename(columns={"index": "sample_idx"})
long_df = long_df.melt(id_vars=["sample_idx"], value_vars=axes, var_name="axis", value_name="value")

if chart_type == "Line":
    chart = alt.Chart(long_df).mark_line().encode(
        x=alt.X("sample_idx:Q", title="Sample"),
        y=alt.Y("value:Q", title="Reading"),
        color="axis:N",
        tooltip=["axis:N", "sample_idx:Q", "value:Q"]
    ).properties(height=350)
    st.altair_chart(chart, use_container_width=True)

elif chart_type == "Scatter":
    chart = alt.Chart(long_df).mark_circle(size=30).encode(
        x=alt.X("sample_idx:Q", title="Sample"),
        y=alt.Y("value:Q", title="Reading"),
        color="axis:N",
        tooltip=["axis:N", "sample_idx:Q", "value:Q"]
    ).properties(height=350)
    st.altair_chart(chart, use_container_width=True)

else:  # Histogram
    chart = alt.Chart(long_df).mark_bar(opacity=0.7).encode(
        x=alt.X("value:Q", bin=alt.Bin(maxbins=40), title="Reading bins"),
        y=alt.Y("count():Q", title="Count"),
        color="axis:N",
        tooltip=["axis:N", "count():Q"]
    ).properties(height=350)
    st.altair_chart(chart, use_container_width=True)

st.subheader("Summary for displayed window")
summary = window_df[axes].agg(["count", "mean", "std", "min", "max"]).T.reset_index().rename(columns={"index": "axis"})
summary["mean"] = summary["mean"].round(4)
summary["std"] = summary["std"].round(4)
st.dataframe(summary, hide_index=True)

# optional auto refresh in watch mode
if data_mode == "Watch folder for latest CSV" and st.sidebar.checkbox("Auto refresh every 10s", value=True):
    st.sidebar.caption("Auto-refresh enabled")
    time.sleep(10)
    st.rerun()

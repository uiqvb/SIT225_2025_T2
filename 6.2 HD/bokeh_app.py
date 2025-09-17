# bokeh_app.py
# SIT225 6.2H — Bokeh Server dashboard
# Run:
#   pip install bokeh pandas numpy
#   bokeh serve --show bokeh_app.py --args ./data
# Or pass a single CSV path instead of a folder.

import sys
from pathlib import Path
import numpy as np
import pandas as pd

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Select, MultiSelect, TextInput, Button, Div, DataTable, TableColumn
from bokeh.plotting import figure

# ---------- data helpers ----------
def list_csvs(folder: Path):
    if not folder.exists():
        return []
    return sorted(folder.glob("*.csv"), key=lambda p: p.stat().st_mtime)

def latest_csv_path(folder: Path):
    files = list_csvs(folder)
    return files[-1] if files else None

def load_csv(path: Path):
    try:
        df = pd.read_csv(path)
    except Exception as e:
        return pd.DataFrame(), f"Error reading {path}: {e}"
    df.columns = [c.strip() for c in df.columns]
    if "sample" not in df.columns:
        df["sample"] = np.arange(len(df))
    return df, f"Loaded: {path.name} ({len(df)} rows)"

def get_axis_options(df: pd.DataFrame):
    preferred = [c for c in ["gyro_x", "gyro_y", "gyro_z"] if c in df.columns]
    if preferred:
        return preferred
    return [c for c in df.select_dtypes(include=[np.number]).columns if c != "sample"]

def clamp(v, lo, hi):
    return max(lo, min(int(v), hi))

# ---------- app state ----------
args = sys.argv[1:]
watch_folder = None
single_csv = None
if len(args) >= 1:
    p = Path(args[0])
    if p.is_dir():
        watch_folder = p
    else:
        single_csv = p

if watch_folder is None and single_csv is None:
    watch_folder = Path("./data")

df = pd.DataFrame()
file_info = "No data loaded yet."

if single_csv:
    df, file_info = load_csv(single_csv)
else:
    newest = latest_csv_path(watch_folder)
    if newest:
        df, file_info = load_csv(newest)

if df.empty:
    df = pd.DataFrame({"sample": [], "gyro_x": [], "gyro_y": [], "gyro_z": []})

axes_default = get_axis_options(df) or []
start_idx = 0
window_n_default = min(200, len(df) if len(df) > 0 else 200)

# ---------- widgets ----------
title = Div(text="<h2>Gyroscope Dashboard — Bokeh</h2>")
file_label = Div(text=f"<b>Data source</b>: {file_info}")

chart_select = Select(title="Chart type", value="Line", options=["Line", "Scatter", "Histogram"])
axis_select = MultiSelect(title="Axes", value=axes_default, options=axes_default, size=4)
n_input = TextInput(title="Number of samples (N)", value=str(window_n_default))

prev_btn = Button(label="Previous")
next_btn = Button(label="Next")

summary_src = ColumnDataSource(dict(axis=[], mean=[], std=[], min=[], max=[]))
summary_table = DataTable(
    source=summary_src,
    columns=[
        TableColumn(field="axis", title="axis"),
        TableColumn(field="mean", title="mean"),
        TableColumn(field="std",  title="std"),
        TableColumn(field="min",  title="min"),
        TableColumn(field="max",  title="max"),
    ],
    width=600, height=200, index_position=None
)

plot = figure(height=350, sizing_mode="stretch_width", x_axis_label="Sample", y_axis_label="Reading")
renderers = []

# ---------- logic ----------
def parse_n():
    try:
        return max(10, int(n_input.value))
    except Exception:
        return 200

def window_slice():
    global start_idx
    n = parse_n()
    L = len(df)
    start = clamp(start_idx, 0, max(0, L - 1))
    end = clamp(start + n, 1, L)
    return start, end

def update_axes_options():
    options = get_axis_options(df)
    axis_select.options = options
    if not axis_select.value or any(a not in options for a in axis_select.value):
        axis_select.value = options

def update_summary(window_df: pd.DataFrame, axes: list[str]):
    if len(window_df) == 0 or len(axes) == 0:
        summary_src.data = dict(axis=[], mean=[], std=[], min=[], max=[])
        return
    s = window_df[axes].agg(["mean", "std", "min", "max"]).T.reset_index().rename(columns={"index": "axis"})
    for col in ["mean", "std", "min", "max"]:
        s[col] = s[col].round(4)
    summary_src.data = s.to_dict(orient="list")

def clear_plot():
    for r in list(renderers):
        try:
            plot.renderers.remove(r)
        except Exception:
            pass
        renderers.remove(r)

def draw_plot():
    clear_plot()
    axes = list(axis_select.value)
    start, end = window_slice()
    window_df = df.iloc[start:end].copy()

    if chart_select.value in ("Line", "Scatter"):
        for axis in axes:
            source = ColumnDataSource(dict(sample=window_df["sample"], value=window_df[axis]))
            if chart_select.value == "Line":
                r = plot.line(x="sample", y="value", source=source, legend_label=axis)
            else:
                r = plot.circle(x="sample", y="value", source=source, legend_label=axis, size=5)
            renderers.append(r)
        plot.legend.visible = True
        plot.xaxis.axis_label = "Sample"
        plot.yaxis.axis_label = "Reading"
    else:
        for axis in axes:
            vals = window_df[axis].dropna().values
            if len(vals) == 0:
                continue
            hist, edges = np.histogram(vals, bins=30)
            source = ColumnDataSource(dict(top=hist, left=edges[:-1], right=edges[1:]))
            r = plot.quad(top="top", bottom=0, left="left", right="right", alpha=0.5, source=source, legend_label=axis)
            renderers.append(r)
        plot.legend.visible = True
        plot.xaxis.axis_label = "Reading bins"
        plot.yaxis.axis_label = "Count"

    update_summary(window_df, axes)

def on_prev():
    global start_idx
    n = parse_n()
    start_idx = max(0, start_idx - n)
    draw_plot()

def on_next():
    global start_idx
    n = parse_n()
    L = len(df)
    start_idx = min(max(0, L - n), start_idx + n)
    draw_plot()

prev_btn.on_click(on_prev)
next_btn.on_click(on_next)

def on_controls_change(attr, old, new):
    draw_plot()

chart_select.on_change("value", on_controls_change)
axis_select.on_change("value", on_controls_change)
n_input.on_change("value", on_controls_change)

def poll_for_new_data():
    global df, file_info, start_idx
    if single_csv:
        return
    newest = latest_csv_path(watch_folder)
    if not newest:
        return
    new_mtime = newest.stat().st_mtime
    last_name = getattr(curdoc(), "_last_file", None)
    last_mtime = getattr(curdoc(), "_last_mtime", 0.0)
    if newest.name != last_name or new_mtime > last_mtime:
        new_df, info = load_csv(newest)
        if not new_df.empty:
            df = new_df
            file_info = info
            curdoc()._last_file = newest.name
            curdoc()._last_mtime = new_mtime
            update_axes_options()
            n = parse_n()
            start_idx = max(0, len(df) - n)
            file_label.text = f"<b>Data source</b>: {file_info}"
            draw_plot()

# initial render
update_axes_options()
draw_plot()

# layout
controls = column(chart_select, axis_select, n_input, row(prev_btn, next_btn), width=350)
layout = row(controls, column(file_label, plot, Div(text="<b>Summary (current window)</b>"), summary_table), sizing_mode="stretch_width")
curdoc().add_root(column(title, layout))

# poll every 10s
curdoc().add_periodic_callback(poll_for_new_data, 10_000)

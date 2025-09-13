# smoothdash.py
"""
Smooth, real-time Plotly Dash updates for continuous data (SIT225 8.2C helper).

Why:
Dash usually redraws a whole figure each update, which looks jumpy.
This wrapper uses Graph.extendData to append small batches like movie frames,
while keeping only a sliding window of recent points. It feels smooth.

API:
    app, state = make_smooth_app(
        channel_names=["X","Y","Z"],
        window_points=600,   # how many points to keep visible per trace
        max_append=20,       # max points appended per frame
        poll_ms=200          # UI polling period in ms
    )
    state["push"](timestamp_str, *values)  # thread-safe producer call
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import List

from dash import Dash, dcc, html, Output, Input, no_update
import plotly.graph_objects as go


@dataclass
class _Shared:
    inbox: deque         # of tuples: (t, v1, v2, ...)
    lock: Lock
    n_channels: int


def make_smooth_app(
    channel_names: List[str],
    window_points: int = 600,
    max_append: int = 20,
    poll_ms: int = 200,
):
    """
    Build a Dash app wired for smooth streaming via extendData.
    Returns (app, state) where state["push"](t, *values) appends to the inbox.
    """
    n = len(channel_names)
    shared = _Shared(deque(), Lock(), n)

    # Empty figure scaffold
    fig = go.Figure()
    for name in channel_names:
        fig.add_trace(go.Scatter(x=[], y=[], mode="lines", name=name))
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis_title="Time",
        yaxis_title="Value",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        uirevision=True,  # keep user zoom while streaming
        title="Live Stream (smooth)",
    )

    app = Dash(__name__)
    app.layout = html.Div(
        style={"fontFamily": "system-ui, -apple-system, Segoe UI, Roboto, Arial", "padding": "12px"},
        children=[
            html.H2("Smooth Live Stream"),
            html.Div(id="stats", style={"marginBottom": "8px"}),
            dcc.Graph(id="g", figure=fig),
            dcc.Interval(id="tick", interval=poll_ms, n_intervals=0),
        ],
    )

    @app.callback(
        Output("g", "extendData"),
        Output("stats", "children"),
        Input("tick", "n_intervals"),
        prevent_initial_call=False,
    )
    def _on_tick(_n):
        # Pop up to max_append samples to draw a small frame
        with shared.lock:
            if not shared.inbox:
                return no_update, "Waiting… inbox=0"
            batch = []
            for _ in range(min(len(shared.inbox), max_append)):
                batch.append(shared.inbox.popleft())

        # batch is [(t, v1, v2, ...)]
        ts = [row[0] for row in batch]
        per_ch = [[] for _ in range(shared.n_channels)]
        for _, *vals in batch:
            for i, v in enumerate(vals):
                per_ch[i].append(v)

        # extendData expects:
        #   ({'x': [ts]*n, 'y': [y0_list, y1_list, ...]}, [trace_indices], max_points)
        extend = {"x": [ts] * shared.n_channels, "y": per_ch}
        trace_idx = list(range(shared.n_channels))
        return (extend, trace_idx, window_points), f"Appended {len(ts)} | inbox={len(shared.inbox)}"

    # thread-safe method to push one sample
    def _push(t, *values):
        if len(values) != n:
            raise ValueError(f"Expected {n} values, got {len(values)}")
        with shared.lock:
            shared.inbox.append((t, *values))

    state = {
        "push": _push,
        "window_points": window_points,
        "max_append": max_append,
        "poll_ms": poll_ms,
        "channels": channel_names,
    }
    return app, state

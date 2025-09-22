# SIT225 7.1P — Linear Regression on DHT22 data with outlier filtering
# Requirements:
#   pip install pandas numpy scikit-learn plotly kaleido
#
# Usage:
#   1) Put your CSV in the same folder or change CSV_PATH below.
#   2) Run: python sit225_7_1p_lr.py
#   3) Outputs will be saved in ./outputs/week-7/

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import plotly.graph_objects as go

# --------------------
# Settings
# --------------------
CSV_PATH = "dht22_data.csv"  # change to your own file if needed
TIME_COL = "Timestamp"
X_COL = "Temperature_C"
Y_COL = "Humidity_%"

OUTPUT_DIR = Path("outputs/week-7")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --------------------
# Helpers
# --------------------
def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # try to parse timestamp if present
    if TIME_COL in df.columns:
        try:
            df[TIME_COL] = pd.to_datetime(df[TIME_COL])
        except Exception:
            pass
    # Keep only needed columns and drop NaNs
    missing = [c for c in [X_COL, Y_COL] if c not in df.columns]
    if missing:
        raise ValueError(f"CSV missing columns: {missing}. Expected {X_COL} and {Y_COL}.")
    return df[[TIME_COL, X_COL, Y_COL]] if TIME_COL in df.columns else df[[X_COL, Y_COL]]

def linspace_between(df: pd.DataFrame, col: str, n: int = 100) -> np.ndarray:
    tmin = float(df[col].min())
    tmax = float(df[col].max())
    return np.linspace(tmin, tmax, n).reshape(-1, 1)

def train_lr(df: pd.DataFrame, x_col: str, y_col: str):
    X = df[[x_col]].values
    y = df[y_col].values
    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)
    slope = float(model.coef_[0])
    intercept = float(model.intercept_)
    r2 = float(r2_score(y, y_pred))
    return model, slope, intercept, r2

def build_fig(df_train: pd.DataFrame, model: LinearRegression, scenario_name: str):
    # predictions along 100 evenly spaced temperatures
    test_temps = linspace_between(df_train, X_COL, n=100)
    test_hums = model.predict(test_temps)

    fig = go.Figure()
    # training scatter
    fig.add_trace(go.Scatter(
        x=df_train[X_COL], y=df_train[Y_COL],
        mode="markers",
        name=f"{scenario_name} data",
        marker=dict(size=6, opacity=0.7)
    ))
    # trend line
    fig.add_trace(go.Scatter(
        x=test_temps.flatten(), y=test_hums,
        mode="lines",
        name=f"{scenario_name} trend"
    ))
    fig.update_layout(
        title=f"Temperature vs Humidity — {scenario_name}",
        xaxis_title="Temperature (°C)",
        yaxis_title="Humidity (%)",
        template="plotly_white",
        legend=dict(x=0.01, y=0.99)
    )
    return fig

def save_fig(fig: go.Figure, base_name: str):
    html_path = OUTPUT_DIR / f"{base_name}.html"
    png_path = OUTPUT_DIR / f"{base_name}.png"
    fig.write_html(str(html_path))
    try:
        # requires kaleido
        fig.write_image(str(png_path), scale=2)
    except Exception as e:
        print(f"PNG save skipped (install kaleido to enable). Reason: {e}")
    print(f"Saved: {html_path}")

def percentile_filter(df: pd.DataFrame, col: str, low_q=0.05, high_q=0.95) -> pd.DataFrame:
    lo = df[col].quantile(low_q)
    hi = df[col].quantile(high_q)
    return df[(df[col] >= lo) & (df[col] <= hi)].copy()

def iqr_filter(df: pd.DataFrame, col: str, k: float = 1.5) -> pd.DataFrame:
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    lo = q1 - k * iqr
    hi = q3 + k * iqr
    return df[(df[col] >= lo) & (df[col] <= hi)].copy()

def print_stats(tag: str, slope: float, intercept: float, r2: float, n: int, x_min: float, x_max: float):
    print(f"\n[{tag}]")
    print(f"  Samples used: {n}")
    print(f"  Temperature range: {x_min:.2f} to {x_max:.2f} °C")
    print(f"  LR equation: Humidity = {slope:.4f} * Temperature + {intercept:.4f}")
    print(f"  R^2: {r2:.4f}")

# --------------------
# Main
# --------------------
def main():
    # Load data
    df = load_data(CSV_PATH)
    df = df.dropna(subset=[X_COL, Y_COL]).copy()

    # Scenario A: Original data
    model_A, slope_A, intercept_A, r2_A = train_lr(df, X_COL, Y_COL)
    fig_A = build_fig(df, model_A, "Original")
    save_fig(fig_A, "scenario_A_original")
    print_stats("Original", slope_A, intercept_A, r2_A, len(df), df[X_COL].min(), df[X_COL].max())

    # Scenario B: Percentile trim (remove extreme low/high temperatures)
    df_B = percentile_filter(df, X_COL, 0.05, 0.95)
    model_B, slope_B, intercept_B, r2_B = train_lr(df_B, X_COL, Y_COL)
    fig_B = build_fig(df_B, model_B, "Filtered P5–P95")
    save_fig(fig_B, "scenario_B_percentile")
    print_stats("Filtered P5–P95", slope_B, intercept_B, r2_B, len(df_B), df_B[X_COL].min(), df_B[X_COL].max())

    # Scenario C: IQR trim
    df_C = iqr_filter(df, X_COL, 1.5)
    model_C, slope_C, intercept_C, r2_C = train_lr(df_C, X_COL, Y_COL)
    fig_C = build_fig(df_C, model_C, "Filtered IQR")
    save_fig(fig_C, "scenario_C_iqr")
    print_stats("Filtered IQR", slope_C, intercept_C, r2_C, len(df_C), df_C[X_COL].min(), df_C[X_COL].max())

    # Combined view to see how trend lines shift
    test_grid = linspace_between(df, X_COL, 100)
    yA = model_A.predict(test_grid)
    yB = model_B.predict(test_grid)
    yC = model_C.predict(test_grid)

    fig_combo = go.Figure()
    fig_combo.add_trace(go.Scatter(x=df[X_COL], y=df[Y_COL], mode="markers",
                                   name="Original data", marker=dict(size=6, opacity=0.5)))
    fig_combo.add_trace(go.Scatter(x=test_grid.flatten(), y=yA, mode="lines", name="Original trend"))
    fig_combo.add_trace(go.Scatter(x=test_grid.flatten(), y=yB, mode="lines", name="P5–P95 trend"))
    fig_combo.add_trace(go.Scatter(x=test_grid.flatten(), y=yC, mode="lines", name="IQR trend"))

    fig_combo.update_layout(
        title="Trend comparison — Original vs Filtered",
        xaxis_title="Temperature (°C)",
        yaxis_title="Humidity (%)",
        template="plotly_white",
        legend=dict(x=0.01, y=0.99)
    )
    save_fig(fig_combo, "scenario_D_trend_comparison")

    # Save small summary table for your report
    summary = pd.DataFrame([
        {"Scenario": "Original", "Samples": len(df), "Slope": slope_A, "Intercept": intercept_A, "R2": r2_A},
        {"Scenario": "Filtered P5–P95", "Samples": len(df_B), "Slope": slope_B, "Intercept": intercept_B, "R2": r2_B},
        {"Scenario": "Filtered IQR", "Samples": len(df_C), "Slope": slope_C, "Intercept": intercept_C, "R2": r2_C},
    ])
    summary_path = OUTPUT_DIR / "lr_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nSaved summary: {summary_path.resolve()}")

if __name__ == "__main__":
    main()

"""make_chart skill: recommend and render bar / line / pie charts with Plotly."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

CHART_TYPES = ("bar", "line", "pie")


def recommend_chart_type(df: pd.DataFrame, preferred: str | None = None) -> str | None:
    if preferred in CHART_TYPES:
        return preferred
    if df is None or df.empty or df.shape[1] < 2:
        return None
    x_col, y_col = _xy_columns(df)
    if x_col is None or y_col is None:
        return None
    sample = df[x_col].astype(str)
    if sample.str.match(r"^\d{4}-\d{2}(-\d{2})?$").mean() >= 0.8:
        return "line"
    share_like = any(
        any(token in str(name).lower() for token in ("pct", "占比", "比例"))
        for name in df.columns
    )
    if share_like and df[x_col].nunique() == len(df) and len(df) <= 12:
        return "pie"
    return "bar"


def _xy_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    numeric = [name for name in df.columns if pd.api.types.is_numeric_dtype(df[name])]
    if not numeric:
        return None, None
    y_col = numeric[-1]
    x_candidates = [name for name in df.columns if name != y_col]
    if not x_candidates:
        return None, None
    return x_candidates[0], y_col


def make_chart(df: pd.DataFrame, chart_type: str | None = None, title: str | None = None) -> Figure | None:
    chosen = recommend_chart_type(df, chart_type)
    if chosen is None:
        return None
    x_col, y_col = _xy_columns(df)
    if x_col is None or y_col is None:
        return None
    data = df.copy()
    data[y_col] = pd.to_numeric(data[y_col], errors="coerce")
    data = data.dropna(subset=[y_col])
    if data.empty:
        return None
    label = title or f"{y_col} by {x_col}"
    if chosen == "line":
        data = data.sort_values(x_col)
        fig = px.line(data, x=x_col, y=y_col, title=label, markers=True)
    elif chosen == "pie":
        fig = px.pie(data, names=x_col, values=y_col, title=label)
    else:
        fig = px.bar(data, x=x_col, y=y_col, title=label, text_auto=True)
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    return fig

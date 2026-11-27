"""compute_stats skill: mean, share, and month-over-month / year-over-year when possible."""
from __future__ import annotations

import pandas as pd


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    return [name for name in df.columns if pd.api.types.is_numeric_dtype(df[name])]


def _category_columns(df: pd.DataFrame) -> list[str]:
    numeric = set(_numeric_columns(df))
    return [name for name in df.columns if name not in numeric]


def compute_stats(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["指标", "值"])

    rows: list[dict[str, object]] = [{"指标": "行数", "值": int(len(df))}]
    numeric = _numeric_columns(df)
    category = _category_columns(df)

    for col in numeric:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            continue
        rows.append({"指标": f"{col} 合计", "值": float(series.sum())})
        rows.append({"指标": f"{col} 均值", "值": float(series.mean())})
        if len(series) > 1 and series.sum() != 0:
            # 占比 only makes sense for part-to-whole breakdowns.
            if len(df) <= 20 and category:
                for _, item in df.iterrows():
                    label = " / ".join(str(item[c]) for c in category)
                    share = 100.0 * float(pd.to_numeric(item[col], errors="coerce") or 0) / float(series.sum())
                    rows.append({"指标": f"{label} 占 {col} 比例(%)", "值": round(share, 2)})

        # If the first column looks like YYYY-MM, compute last two points' 环比.
        if category and _looks_like_month(df[category[0]]):
            mom = _mom_from_monthly(df, category[0], col)
            if mom is not None:
                rows.append({"指标": f"{col} 最近一月环比(%)", "值": mom})

    return pd.DataFrame(rows)


def _looks_like_month(series: pd.Series) -> bool:
    if series.empty:
        return False
    return bool(series.astype(str).str.match(r"^\d{4}-\d{2}$").mean() >= 0.8)


def _mom_from_monthly(df: pd.DataFrame, month_col: str, value_col: str) -> float | None:
    ordered = df[[month_col, value_col]].copy()
    ordered[value_col] = pd.to_numeric(ordered[value_col], errors="coerce")
    ordered = ordered.dropna().sort_values(month_col)
    if len(ordered) < 2:
        return None
    prev = float(ordered.iloc[-2][value_col])
    curr = float(ordered.iloc[-1][value_col])
    if prev == 0:
        return None
    return round(100.0 * (curr - prev) / prev, 2)

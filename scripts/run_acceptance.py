"""Run the 10 acceptance queries against the sample data and print results."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data_mcp.datasources import fetch_rows
from data_mcp.security import assert_readonly_select, ensure_limit

CASES = [
    (
        "各个区域的销售总额是多少？（柱状图）",
        "SELECT region, SUM(amount) AS total_amount FROM sales GROUP BY region ORDER BY total_amount DESC",
    ),
    (
        "各个类别的销售额占比是多少？（饼图）",
        "SELECT category, SUM(amount) AS total_amount FROM sales GROUP BY category",
    ),
    (
        "按月的销售额趋势是怎样的？（折线图）",
        "SELECT strftime('%Y-%m', sale_date) AS ym, SUM(amount) AS total_amount FROM sales GROUP BY ym ORDER BY ym",
    ),
    (
        "销售额最高的 5 个商品是哪些？",
        "SELECT product, SUM(amount) AS total_amount FROM sales GROUP BY product ORDER BY total_amount DESC LIMIT 5",
    ),
    (
        "全部订单的平均金额是多少？",
        "SELECT AVG(amount) AS avg_amount FROM sales",
    ),
    (
        "华东地区一共卖了多少件？",
        "SELECT SUM(qty) AS total_qty FROM sales WHERE region = '华东'",
    ),
    (
        "2025 年 10 月比 9 月的销售额环比是多少？",
        "SELECT ROUND(100.0 * (SUM(CASE WHEN strftime('%Y-%m', sale_date)='2025-10' THEN amount ELSE 0 END) - SUM(CASE WHEN strftime('%Y-%m', sale_date)='2025-09' THEN amount ELSE 0 END)) / SUM(CASE WHEN strftime('%Y-%m', sale_date)='2025-09' THEN amount ELSE NULL END), 2) AS mom_pct FROM sales",
    ),
    (
        "2025 年 10 月和 2024 年 10 月的销售额同比是多少？",
        "SELECT ROUND(100.0 * (SUM(CASE WHEN strftime('%Y-%m', sale_date)='2025-10' THEN amount ELSE 0 END) - SUM(CASE WHEN strftime('%Y-%m', sale_date)='2024-10' THEN amount ELSE 0 END)) / SUM(CASE WHEN strftime('%Y-%m', sale_date)='2024-10' THEN amount ELSE NULL END), 2) AS yoy_pct FROM sales",
    ),
    (
        "每个商品的销售毛利是多少？（关联 Excel 成本表）",
        "SELECT s.product, SUM(s.amount) - SUM(s.qty * p.unit_cost) AS gross_profit FROM sales s JOIN products p ON s.product = p.product GROUP BY s.product ORDER BY gross_profit DESC",
    ),
    (
        "手机类别的销售额占全部的比例是多少？",
        "SELECT ROUND(100.0 * SUM(CASE WHEN category='手机' THEN amount ELSE 0 END) / SUM(amount), 2) AS phone_pct FROM sales",
    ),
]


def main() -> None:
    for index, (title, sql) in enumerate(CASES, start=1):
        cleaned = assert_readonly_select(sql)
        limited = ensure_limit(cleaned)
        rows = fetch_rows(limited)
        print(f"\n{index}. {title}")
        print(sql)
        print(json.dumps(rows, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()

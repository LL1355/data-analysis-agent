"""Generate reproducible sample data for topic 5.

Creates:
  - data/sales.db        SQLite table sales
  - data/products.xlsx   Excel sheet products
"""
from __future__ import annotations

import random
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent
SALES_DB = DATA_DIR / "sales.db"
PRODUCTS_XLSX = DATA_DIR / "products.xlsx"

PRODUCTS = [
    {"product": "iPhone 16", "category": "手机", "unit_cost": 4800, "unit_price": 5999},
    {"product": "华为 Mate 70", "category": "手机", "unit_cost": 4200, "unit_price": 5499},
    {"product": "MacBook Air", "category": "电脑", "unit_cost": 6500, "unit_price": 7999},
    {"product": "ThinkPad X1", "category": "电脑", "unit_cost": 7200, "unit_price": 8999},
    {"product": "AirPods", "category": "配件", "unit_cost": 800, "unit_price": 1299},
    {"product": "机械键盘", "category": "配件", "unit_cost": 350, "unit_price": 599},
]

REGIONS = ["华东", "华南", "华北"]
# Base monthly demand by region, so 华东 stays clearly largest.
REGION_FACTOR = {"华东": 1.35, "华南": 1.05, "华北": 0.85}

# Cover two years and many months, including 2024-10 / 2025-09 / 2025-10
# for year-over-year and month-over-month questions.
MONTHS = [(year, month) for year in (2024, 2025) for month in range(1, 13) if not (year == 2025 and month > 10)]


def build_frames(seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = random.Random(seed)
    rows: list[dict] = []
    for year, month in MONTHS:
        # 2025 is slightly stronger than 2024; 2025-10 is stronger than 2025-09.
        year_factor = 1.18 if year == 2025 else 1.0
        if year == 2025 and month == 10:
            month_factor = 1.22
        elif year == 2025 and month == 9:
            month_factor = 0.96
        else:
            month_factor = 1.0 + ((month - 6) * 0.015)
        for region in REGIONS:
            for item in PRODUCTS:
                qty = max(
                    1,
                    int(round(rng.randint(4, 16) * REGION_FACTOR[region] * year_factor * month_factor)),
                )
                # Occasional mid-month day variation, still within the month.
                day = rng.choice([5, 8, 12, 15, 18, 22, 26])
                rows.append(
                    {
                        "sale_date": date(year, month, day).isoformat(),
                        "region": region,
                        "category": item["category"],
                        "product": item["product"],
                        "qty": qty,
                        "amount": qty * item["unit_price"],
                    }
                )
    sales = pd.DataFrame(rows)
    products = pd.DataFrame(
        [{"product": p["product"], "category": p["category"], "unit_cost": p["unit_cost"]} for p in PRODUCTS]
    )
    return sales, products


def write_files(sales: pd.DataFrame, products: pd.DataFrame) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if SALES_DB.exists():
        SALES_DB.unlink()
    with sqlite3.connect(SALES_DB) as con:
        sales.to_sql("sales", con, index=False, if_exists="replace")
        con.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date);
            """
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_sales_region ON sales(region);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product);")
    products.to_excel(PRODUCTS_XLSX, sheet_name="products", index=False)


def main() -> None:
    sales, products = build_frames()
    write_files(sales, products)
    print(f"wrote {SALES_DB} ({len(sales)} rows)")
    print(f"wrote {PRODUCTS_XLSX} ({len(products)} rows)")
    print("regions:", ", ".join(sorted(sales["region"].unique())))
    print("months:", sales["sale_date"].min(), "->", sales["sale_date"].max())


if __name__ == "__main__":
    main()

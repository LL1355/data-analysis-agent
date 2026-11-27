"""Load SQLite sales and Excel products into a read-only in-memory database."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SALES_DB = DATA_DIR / "sales.db"
PRODUCTS_XLSX = DATA_DIR / "products.xlsx"

ALLOWED_TABLES = ("sales", "products")


def _require_files() -> None:
    missing = [str(path) for path in (SALES_DB, PRODUCTS_XLSX) if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "缺少样例数据文件: "
            + ", ".join(missing)
            + "。请先运行 python data/generate_sample_data.py"
        )


def _load_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    _require_files()
    # Official stack: SQLAlchemy for SQLite, pandas for Excel.
    source = create_engine(f"sqlite+pysqlite:///file:{SALES_DB.as_posix()}?mode=ro&uri=true")
    try:
        sales = pd.read_sql(
            text("SELECT sale_date, region, category, product, qty, amount FROM sales"),
            source,
        )
    finally:
        source.dispose()
    products = pd.read_excel(PRODUCTS_XLSX, sheet_name="products")
    expected = {"product", "category", "unit_cost"}
    if not expected.issubset(set(products.columns)):
        raise ValueError(
            f"products.xlsx 列名不正确，需要 {sorted(expected)}，实际是 {list(products.columns)}"
        )
    return sales, products[list(expected)]


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """In-memory SQLite copy so source files stay untouched and JOINs share one engine.

    Queries use the SQLite dialect, matching the 10 acceptance statements
    (including strftime('%Y-%m', sale_date)).
    """
    sales, products = _load_frames()
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sales.to_sql("sales", engine, index=False, if_exists="replace")
    products.to_sql("products", engine, index=False, if_exists="replace")

    @event.listens_for(engine, "connect")
    def _restrict_write(dbapi_conn, _connection_record):  # type: ignore[no-untyped-def]
        dbapi_conn.execute("PRAGMA query_only = ON")

    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA query_only = ON")
        conn.commit()
    return engine


def list_tables() -> list[dict[str, str]]:
    return [
        {"name": "sales", "source": "SQLite", "path": str(SALES_DB)},
        {"name": "products", "source": "Excel", "path": str(PRODUCTS_XLSX)},
    ]


def describe_table(table: str) -> list[dict[str, str]]:
    name = normalize_table(table)
    inspector = inspect(get_engine())
    return [
        {
            "name": col["name"],
            "type": str(col["type"]),
            "nullable": "YES" if col["nullable"] else "NO",
        }
        for col in inspector.get_columns(name)
    ]


def normalize_table(table: str) -> str:
    name = (table or "").strip()
    if name not in ALLOWED_TABLES:
        raise ValueError(f"未知表: {table}。可选表: {', '.join(ALLOWED_TABLES)}")
    return name


def fetch_rows(sql: str) -> list[dict]:
    with get_engine().connect() as conn:
        result = conn.execute(text(sql))
        return [dict(row._mapping) for row in result]
